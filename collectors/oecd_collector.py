# -*- coding: utf-8 -*-
"""Collect selected OECD monthly macro indicators through the OECD SDMX API."""

from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CACHE_DIR, COUNTRIES, DATA_RAW, OECD_SERIES

OUT_FILE = DATA_RAW / "oecd_raw.csv"
OECD_CACHE_DIR = CACHE_DIR / "oecd"
OECD_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _read_csv(indicator_code: str, url: str, force_refresh: bool = False) -> pd.DataFrame:
    cache_path = OECD_CACHE_DIR / f"{indicator_code}.csv"
    if cache_path.exists() and not force_refresh:
        return pd.read_csv(cache_path)

    resp = _session().get(url, timeout=60, headers={"Accept": "text/csv"})
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return pd.read_csv(StringIO(resp.text))


def collect_oecd(force_refresh: bool = False) -> pd.DataFrame:
    rows = []
    iso3_to_code = {info["iso3"]: code for code, info in COUNTRIES.items()}
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")

    for indicator_code, meta in OECD_SERIES.items():
        df = _read_csv(indicator_code, meta["url"], force_refresh)
        required = {"REF_AREA", "TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(df.columns):
            raise ValueError(f"Unexpected OECD schema for {indicator_code}: {df.columns.tolist()}")

        df = df[df["REF_AREA"].isin(iso3_to_code.keys())].copy()
        for _, row in df.iterrows():
            country_code = iso3_to_code.get(row["REF_AREA"])
            if not country_code:
                continue
            country = COUNTRIES[country_code]
            value = pd.to_numeric(row.get("OBS_VALUE"), errors="coerce")
            rows.append(
                {
                    "series_id": f"{country_code}.{indicator_code}.OECD",
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
                    "source_organization": "OECD",
                    "source_dataset": "Prices: Consumer prices",
                    "source_indicator_code": meta["source_series_code"],
                    "source_indicator_name": meta["indicator_name_en"],
                    "source_url": meta["url"],
                    "last_updated": data_version,
                    "status": str(row.get("OBS_STATUS", "final")) or "final",
                    "retrieved_at": retrieved_at,
                    "data_version": data_version,
                }
            )

    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[OECD] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_oecd()
