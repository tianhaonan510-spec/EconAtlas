# -*- coding: utf-8 -*-
"""Collect selected ECB data through the ECB Data Portal API."""

from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CACHE_DIR, COUNTRIES, DATA_RAW, ECB_SERIES

OUT_FILE = DATA_RAW / "ecb_raw.csv"
ECB_CACHE_DIR = CACHE_DIR / "ecb"
ECB_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _read_csv(indicator_code: str, meta: dict, force_refresh: bool = False) -> pd.DataFrame:
    url = (
        f"https://data-api.ecb.europa.eu/service/data/{meta['flow']}/{meta['key']}"
        "?startPeriod=2015-01-01"
    )
    cache_path = ECB_CACHE_DIR / f"{indicator_code}.csv"
    if cache_path.exists() and not force_refresh:
        return pd.read_csv(cache_path)

    resp = _session().get(url, timeout=60, headers={"Accept": "text/csv"})
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return pd.read_csv(StringIO(resp.text))


def collect_ecb(force_refresh: bool = False) -> pd.DataFrame:
    rows = []
    country = COUNTRIES["EA"]
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")

    for indicator_code, meta in ECB_SERIES.items():
        df = _read_csv(indicator_code, meta, force_refresh)
        required = {"TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(df.columns):
            raise ValueError(f"Unexpected ECB schema for {indicator_code}: {df.columns.tolist()}")

        for _, row in df.iterrows():
            value = pd.to_numeric(row.get("OBS_VALUE"), errors="coerce")
            rows.append(
                {
                    "series_id": f"EA.{indicator_code}.ECB",
                    "country_code": "EA",
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
                    "source_organization": "ECB",
                    "source_dataset": "Euro foreign exchange reference rates",
                    "source_indicator_code": meta["source_series_code"],
                    "source_indicator_name": meta["indicator_name_en"],
                    "source_url": f"https://data.ecb.europa.eu/data/datasets/{meta['flow']}/{meta['key']}",
                    "last_updated": data_version,
                    "status": str(row.get("OBS_STATUS", "final")) or "final",
                    "retrieved_at": retrieved_at,
                    "data_version": data_version,
                }
            )

    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[ECB] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_ecb()
