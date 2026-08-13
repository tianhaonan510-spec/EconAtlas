# -*- coding: utf-8 -*-
"""Collect selected BIS statistics through the BIS SDMX CSV API."""

import time
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import BIS_SERIES, CACHE_DIR, COUNTRIES, DATA_RAW

OUT_FILE = DATA_RAW / "bis_raw.csv"
BIS_CACHE_DIR = CACHE_DIR / "bis"
BIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

BIS_AREA_MAP = {"EA": "XM"}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _bis_area(country_code: str) -> str:
    return BIS_AREA_MAP.get(country_code, country_code)


def _read_country_csv(indicator_code: str, country_code: str, force_refresh: bool = False) -> pd.DataFrame:
    bis_area = _bis_area(country_code)
    cache_path = BIS_CACHE_DIR / f"{indicator_code}_{country_code}.csv"
    if cache_path.exists() and not force_refresh:
        return pd.read_csv(cache_path)

    url = f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_XRU/1.0/D.{bis_area}..?format=csv&startPeriod=2015-01-01"
    resp = _session().get(url, timeout=60)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return pd.read_csv(StringIO(resp.text))


def _platform_country(ref_area: str):
    reverse = {"XM": "EA"}
    mapped = reverse.get(str(ref_area), str(ref_area))
    if mapped in COUNTRIES:
        return mapped
    return None


def collect_bis(force_refresh: bool = False) -> pd.DataFrame:
    rows = []
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")

    for indicator_code, meta in BIS_SERIES.items():
        frames = []
        for country_code in meta.get("countries", []):
            try:
                frames.append(_read_country_csv(indicator_code, country_code, force_refresh))
                time.sleep(0.15)
            except Exception as exc:
                print(f"[BIS] failed {country_code}: {exc}")
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        required = {"REF_AREA", "TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(df.columns):
            raise ValueError(f"Unexpected BIS schema for {indicator_code}: {df.columns.tolist()}")

        target_countries = set(meta.get("countries", []))
        for _, row in df.iterrows():
            country_code = _platform_country(row.get("REF_AREA"))
            if not country_code or country_code not in target_countries:
                continue
            country = COUNTRIES[country_code]
            value = pd.to_numeric(row.get("OBS_VALUE"), errors="coerce")
            rows.append(
                {
                    "series_id": f"{country_code}.{indicator_code}.BIS",
                    "country_code": country_code,
                    "country_iso2": country["iso2"],
                    "country_iso3": country["iso3"],
                    "country_name_zh": country["zh"],
                    "country_name_en": country["en"],
                    "indicator_code": indicator_code,
                    "indicator_name_zh": meta["indicator_name_zh"],
                    "indicator_name_en": meta["indicator_name_en"],
                    "date": str(row["TIME_PERIOD"]),
                    "frequency": meta["frequency"],
                    "unit": meta["unit"],
                    "seasonal_adjustment": meta["seasonal_adjustment"],
                    "calculation": meta["calculation"],
                    "value": None if pd.isna(value) else float(value),
                    "source_organization": "BIS",
                    "source_dataset": "Exchange rates",
                    "source_indicator_code": meta["source_series_code"],
                    "source_indicator_name": str(row.get("TITLE", meta["indicator_name_en"])),
                    "source_url": "https://stats.bis.org/",
                    "last_updated": data_version,
                    "status": str(row.get("OBS_STATUS", "final")) or "final",
                    "retrieved_at": retrieved_at,
                    "data_version": data_version,
                }
            )

    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[BIS] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_bis()
