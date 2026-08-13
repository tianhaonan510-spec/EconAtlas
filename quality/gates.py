"""Blocking quality gates for publishing an EconAtlas data snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import DATA_CLEAN, METADATA_DIR


OUT_FILE = DATA_CLEAN / "quality_gate.json"


def run_quality_gates(raise_on_failure: bool = True) -> dict:
    data = pd.read_csv(DATA_CLEAN / "macro_observations.csv", encoding="utf-8-sig", low_memory=False)
    master = pd.read_csv(METADATA_DIR / "indicator_master.csv", encoding="utf-8-sig", low_memory=False)
    value = pd.to_numeric(data["value"], errors="coerce")
    key = ["country_code", "indicator_code", "date", "source_organization", "source_dataset"]
    required = [
        "country_code", "indicator_code", "date", "frequency", "unit", "value",
        "source_organization", "source_dataset", "source_indicator_code", "source_url",
        "observation_type", "processing_level", "source_status", "data_version",
    ]
    missing_columns = [column for column in required if column not in data.columns]
    future_year = pd.to_numeric(data["date"].astype(str).str[:4], errors="coerce") > pd.Timestamp.now().year
    forecast_mislabeled = int((future_year & data.get("observation_type", pd.Series("", index=data.index)).ne("forecast") & data["source_organization"].eq("IMF")).sum())
    checks = {
        "required_columns_present": {"passed": not missing_columns, "detail": missing_columns},
        "no_null_observations": {"passed": int(value.isna().sum()) == 0, "detail": int(value.isna().sum())},
        "no_duplicate_business_keys": {"passed": int(data.duplicated(key).sum()) == 0, "detail": int(data.duplicated(key).sum())},
        "all_indicators_registered": {
            "passed": set(data["indicator_code"].dropna()).issubset(set(master["indicator_code"].dropna())),
            "detail": sorted(set(data["indicator_code"].dropna()) - set(master["indicator_code"].dropna())),
        },
        "forecast_semantics_valid": {"passed": forecast_mislabeled == 0, "detail": forecast_mislabeled},
        "source_urls_complete": {"passed": int(data["source_url"].isna().sum()) == 0, "detail": int(data["source_url"].isna().sum())},
    }
    payload = {
        "status": "passed" if all(item["passed"] for item in checks.values()) else "failed",
        "row_count": int(len(data)),
        "checks": checks,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if raise_on_failure and payload["status"] != "passed":
        raise RuntimeError(f"Data quality gate failed; see {OUT_FILE}")
    return payload


if __name__ == "__main__":
    print(json.dumps(run_quality_gates(), ensure_ascii=False, indent=2))
