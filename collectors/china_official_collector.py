# -*- coding: utf-8 -*-
"""Import official China monthly macro data from local CSV files.

The National Bureau of Statistics website does not provide a consistently stable
public JSON endpoint for unattended batch jobs. This importer keeps the pipeline
reproducible: download official CSV/Excel data from data.stats.gov.cn, normalize
it to the template in data_raw/china_official/README.md, then run this collector.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from config import CHINA_OFFICIAL_SERIES, COUNTRIES, DATA_RAW

SOURCE_DIR = DATA_RAW / "china_official"
OUT_FILE = DATA_RAW / "china_official_raw.csv"


def _empty_standard_table():
    return pd.DataFrame(
        columns=[
            "series_id", "country_code", "country_iso2", "country_iso3", "country_name_zh",
            "country_name_en", "indicator_code", "indicator_name_zh", "indicator_name_en",
            "date", "frequency", "unit", "seasonal_adjustment", "calculation", "value",
            "source_organization", "source_dataset", "source_indicator_code",
            "source_indicator_name", "source_url", "last_updated", "status",
            "retrieved_at", "data_version",
        ]
    )


def _load_input_files():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SOURCE_DIR.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    frames = [pd.read_csv(path, encoding="utf-8-sig") for path in files]
    return pd.concat(frames, ignore_index=True)


def collect_china_official() -> pd.DataFrame:
    raw = _load_input_files()
    if raw.empty:
        out = _empty_standard_table()
        out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
        print(f"[ChinaOfficial] no local files found, wrote empty table: {OUT_FILE}")
        return out

    required = {"indicator_code", "date", "value"}
    if not required.issubset(raw.columns):
        raise ValueError(f"China official input requires columns {sorted(required)}; got {raw.columns.tolist()}")

    country = COUNTRIES["CN"]
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_version = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for _, row in raw.iterrows():
        indicator_code = row["indicator_code"]
        if indicator_code not in CHINA_OFFICIAL_SERIES:
            continue
        meta = CHINA_OFFICIAL_SERIES[indicator_code]
        value = pd.to_numeric(row.get("value"), errors="coerce")
        rows.append(
            {
                "series_id": f"CN.{indicator_code}.NBS",
                "country_code": "CN",
                "country_iso2": country["iso2"],
                "country_iso3": country["iso3"],
                "country_name_zh": country["zh"],
                "country_name_en": country["en"],
                "indicator_code": indicator_code,
                "indicator_name_zh": meta["indicator_name_zh"],
                "indicator_name_en": meta["indicator_name_en"],
                "date": str(row["date"]),
                "frequency": meta["frequency"],
                "unit": meta["unit"],
                "seasonal_adjustment": meta["seasonal_adjustment"],
                "calculation": meta["calculation"],
                "value": None if pd.isna(value) else float(value),
                "source_organization": "National Bureau of Statistics of China",
                "source_dataset": meta["source_dataset"],
                "source_indicator_code": meta["source_series_code"],
                "source_indicator_name": meta["indicator_name_en"],
                "source_url": str(row.get("source_url", "https://data.stats.gov.cn/")),
                "last_updated": str(row.get("last_updated", data_version)),
                "status": str(row.get("status", "official")),
                "retrieved_at": retrieved_at,
                "data_version": str(row.get("data_version", data_version)),
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[ChinaOfficial] saved: {OUT_FILE}, shape={out.shape}")
    return out


if __name__ == "__main__":
    collect_china_official()
