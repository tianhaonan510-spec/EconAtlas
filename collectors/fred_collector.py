# -*- coding: utf-8 -*-
"""Collect selected monthly U.S. macro indicators from FRED graph CSV endpoints."""

from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CACHE_DIR, COUNTRIES, DATA_RAW, FRED_SERIES

OUT_FILE = DATA_RAW / "fred_raw.csv"
FRED_CACHE_DIR = CACHE_DIR / "fred"
FRED_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _cache_path(series_id: str):
    return FRED_CACHE_DIR / f"{series_id}.csv"


def _read_series_csv(series_id: str, force_refresh: bool = False) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    cache_path = _cache_path(series_id)
    if cache_path.exists() and not force_refresh:
        return pd.read_csv(cache_path)

    resp = _session().get(url, timeout=30)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return pd.read_csv(StringIO(resp.text))


def collect_fred(force_refresh: bool = False) -> pd.DataFrame:
    rows = []
    country = COUNTRIES["US"]
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")

    for indicator_code, meta in FRED_SERIES.items():
        series_id = meta["fred_series_id"]
        df = _read_series_csv(series_id, force_refresh)
        if "observation_date" not in df.columns or series_id not in df.columns:
            raise ValueError(f"Unexpected FRED CSV schema for {series_id}: {df.columns.tolist()}")

        df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
        df = df[df["observation_date"].notna()].copy()
        df = df[df["observation_date"].dt.year >= 2015]

        for _, row in df.iterrows():
            value = pd.to_numeric(row.get(series_id), errors="coerce")
            rows.append(
                {
                    "series_id": f"US.{indicator_code}.FRED",
                    "country_code": "US",
                    "country_iso2": country["iso2"],
                    "country_iso3": country["iso3"],
                    "country_name_zh": country["zh"],
                    "country_name_en": country["en"],
                    "indicator_code": indicator_code,
                    "indicator_name_zh": meta["indicator_name_zh"],
                    "indicator_name_en": meta["indicator_name_en"],
                    "date": row["observation_date"].strftime("%Y-%m"),
                    "frequency": meta.get("frequency", "M"),
                    "unit": meta["unit"],
                    "seasonal_adjustment": meta["seasonal_adjustment"],
                    "calculation": meta["calculation"],
                    "value": None if pd.isna(value) else float(value),
                    "source_organization": "FRED",
                    "source_dataset": "Federal Reserve Economic Data",
                    "source_indicator_code": series_id,
                    "source_indicator_name": meta["indicator_name_en"],
                    "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                    "last_updated": data_version,
                    "status": "final",
                    "retrieved_at": retrieved_at,
                    "data_version": data_version,
                }
            )

    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[FRED] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_fred()

