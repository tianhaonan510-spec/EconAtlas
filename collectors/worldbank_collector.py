# -*- coding: utf-8 -*-
import json
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CACHE_DIR, COUNTRIES, DATA_RAW, END_YEAR, INDICATOR_MAP, LOG_DIR, START_YEAR

DATA_RAW.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
WB_CACHE_DIR = CACHE_DIR / "worldbank"
WB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "collect.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _cache_path(country_iso2: str, source_series_code: str, start_year: int, end_year: int):
    safe_code = source_series_code.replace(".", "_")
    return WB_CACHE_DIR / f"{country_iso2}_{safe_code}_{start_year}_{end_year}.json"


def _load_or_fetch_json(url: str, cache_path, force_refresh: bool = False) -> Any:
    if cache_path.exists() and not force_refresh:
        logging.info("World Bank cache hit: %s", cache_path)
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    resp = _session().get(url, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    logging.info("World Bank cache saved: %s", cache_path)
    return payload


def _fetch_one(country_iso2: str, source_series_code: str, start_year: int, end_year: int, force_refresh: bool = False):
    url = (
        f"https://api.worldbank.org/v2/country/{country_iso2}/indicator/{source_series_code}"
        f"?format=json&per_page=20000&date={start_year}:{end_year}"
    )
    payload = _load_or_fetch_json(url, _cache_path(country_iso2, source_series_code, start_year, end_year), force_refresh)
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return []

    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for item in payload[1]:
        rows.append(
            {
                "country_code": country_iso2,
                "country_name": item.get("country", {}).get("value"),
                "source_indicator_code": source_series_code,
                "source_indicator_name": item.get("indicator", {}).get("value"),
                "date": item.get("date"),
                "value": item.get("value"),
                "source_organization": "World Bank",
                "source_dataset": "World Development Indicators",
                "source_url": url,
                "retrieved_at": retrieved_at,
                "last_updated": data_version,
                "status": "final",
                "data_version": data_version,
            }
        )
    return rows


def collect_worldbank(force_refresh: bool = False) -> pd.DataFrame:
    all_rows = []
    source_codes = sorted(
        {
            src["source_series_code"]
            for meta in INDICATOR_MAP.values()
            for src in meta["sources"]
            if src["organization"] == "World Bank"
        }
    )
    total = len(COUNTRIES) * len(source_codes)
    done = 0
    for country_iso2 in COUNTRIES:
        for source_code in source_codes:
            done += 1
            try:
                rows = _fetch_one(country_iso2, source_code, START_YEAR, END_YEAR, force_refresh)
                all_rows.extend(rows)
                logging.info("World Bank OK %s/%s: %s %s rows=%s", done, total, country_iso2, source_code, len(rows))
                print(f"[WorldBank] {done}/{total} {country_iso2} {source_code}: {len(rows)} rows")
                if not _cache_path(country_iso2, source_code, START_YEAR, END_YEAR).exists() or force_refresh:
                    time.sleep(0.05)
            except Exception as exc:
                logging.exception("World Bank FAILED: %s %s: %s", country_iso2, source_code, exc)
                print(f"[WorldBank] FAILED {country_iso2} {source_code}: {exc}")

    df = pd.DataFrame(all_rows)
    out = DATA_RAW / "worldbank_raw.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[WorldBank] saved: {out}, shape={df.shape}")
    return df


if __name__ == "__main__":
    collect_worldbank()


