# -*- coding: utf-8 -*-
"""Collect selected Eurostat indicators through the dissemination statistics API."""

import json
from datetime import datetime
from itertools import product

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CACHE_DIR, COUNTRIES, DATA_RAW, EUROSTAT_SERIES

OUT_FILE = DATA_RAW / "eurostat_raw.csv"
EUROSTAT_CACHE_DIR = CACHE_DIR / "eurostat"
EUROSTAT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

GEO_TO_COUNTRY = {"EA20": "EA", "DE": "DE", "FR": "FR", "IT": "IT", "ES": "ES"}


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _fetch_json(indicator_code: str, meta: dict, force_refresh: bool = False) -> dict:
    base = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{meta['dataset']}"
    params = {"sinceTimePeriod": "2015"}
    params.update(meta.get("params", {}))
    for geo in meta["geos"]:
        params.setdefault("geo", [])
        params["geo"].append(geo)

    cache_path = EUROSTAT_CACHE_DIR / f"{indicator_code}.json"
    if cache_path.exists() and not force_refresh:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    resp = _session().get(base, params=params, timeout=60)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return resp.json()


def _dimension_codes(dataset: dict, dimension_id: str):
    category = dataset["dimension"][dimension_id]["category"]
    index_map = category["index"]
    labels = category.get("label", {})
    ordered = sorted(index_map.items(), key=lambda item: item[1])
    return [(code, labels.get(code, code)) for code, _ in ordered]


def _flatten_values(dataset: dict):
    ids = dataset["id"]
    sizes = dataset["size"]
    code_lists = [_dimension_codes(dataset, dim_id) for dim_id in ids]
    values = dataset.get("value", {})
    for flat_index, combo in enumerate(product(*code_lists)):
        key = str(flat_index)
        if key not in values:
            continue
        yield {dim_id: combo[i][0] for i, dim_id in enumerate(ids)}, values[key]


def collect_eurostat(force_refresh: bool = False) -> pd.DataFrame:
    rows = []
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")

    for indicator_code, meta in EUROSTAT_SERIES.items():
        dataset = _fetch_json(indicator_code, meta, force_refresh)
        for dims, value in _flatten_values(dataset):
            country_code = GEO_TO_COUNTRY.get(dims.get("geo"))
            if not country_code:
                continue
            country = COUNTRIES[country_code]
            obs_value = pd.to_numeric(value, errors="coerce")
            rows.append(
                {
                    "series_id": f"{country_code}.{indicator_code}.EUROSTAT",
                    "country_code": country_code,
                    "country_iso2": country["iso2"],
                    "country_iso3": country["iso3"],
                    "country_name_zh": country["zh"],
                    "country_name_en": country["en"],
                    "indicator_code": indicator_code,
                    "indicator_name_zh": meta["indicator_name_zh"],
                    "indicator_name_en": meta["indicator_name_en"],
                    "date": dims.get("time"),
                    "frequency": meta["frequency"],
                    "unit": meta["unit"],
                    "seasonal_adjustment": meta["seasonal_adjustment"],
                    "calculation": meta["calculation"],
                    "value": None if pd.isna(obs_value) else float(obs_value),
                    "source_organization": "Eurostat",
                    "source_dataset": meta["dataset"],
                    "source_indicator_code": meta["source_series_code"],
                    "source_indicator_name": meta["indicator_name_en"],
                    "source_url": f"https://ec.europa.eu/eurostat/databrowser/view/{meta['dataset']}/default/table",
                    "last_updated": dataset.get("updated", data_version),
                    "status": "final",
                    "retrieved_at": retrieved_at,
                    "data_version": dataset.get("updated", data_version),
                }
            )

    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[Eurostat] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_eurostat()
