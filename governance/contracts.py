"""Executable data contracts used before an EconAtlas snapshot is published."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "country_code", "indicator_code", "date", "frequency", "unit", "value",
    "source_organization", "source_dataset", "source_indicator_code", "source_url",
    "observation_type", "processing_level", "source_status", "release_status", "data_version",
]
BUSINESS_KEY = ["country_code", "indicator_code", "date", "source_organization", "source_dataset"]
OBSERVATION_TYPES = {"historical", "derived", "forecast"}
PROCESSING_LEVELS = {"standardized", "derived"}
RELEASE_STATUSES = {"preliminary", "final", "revised", "estimated", "unknown"}
FREQUENCIES = {"D", "W", "M", "Q", "A"}


def evaluate_contracts(data: pd.DataFrame, indicator_master: pd.DataFrame) -> dict[str, dict[str, Any]]:
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    checks: dict[str, dict[str, Any]] = {
        "required_columns_present": {"passed": not missing, "detail": missing},
    }
    if missing:
        return checks
    values = pd.to_numeric(data["value"], errors="coerce")
    years = pd.to_numeric(data["date"].astype(str).str.extract(r"^(\d{4})", expand=False), errors="coerce")
    today_year = datetime.now().year
    registered = set(indicator_master.get("indicator_code", pd.Series(dtype=str)).dropna().astype(str))
    checks.update({
        "values_are_numeric": {"passed": int(values.isna().sum()) == 0, "detail": int(values.isna().sum())},
        "business_keys_are_unique": {"passed": int(data.duplicated(BUSINESS_KEY).sum()) == 0, "detail": int(data.duplicated(BUSINESS_KEY).sum())},
        "indicators_are_registered": {"passed": set(data["indicator_code"].dropna().astype(str)).issubset(registered), "detail": sorted(set(data["indicator_code"].dropna().astype(str)) - registered)},
        "observation_type_enum": {"passed": set(data["observation_type"].dropna().astype(str)).issubset(OBSERVATION_TYPES), "detail": sorted(set(data["observation_type"].dropna().astype(str)) - OBSERVATION_TYPES)},
        "processing_level_enum": {"passed": set(data["processing_level"].dropna().astype(str)).issubset(PROCESSING_LEVELS), "detail": sorted(set(data["processing_level"].dropna().astype(str)) - PROCESSING_LEVELS)},
        "release_status_enum": {"passed": set(data["release_status"].dropna().astype(str)).issubset(RELEASE_STATUSES), "detail": sorted(set(data["release_status"].dropna().astype(str)) - RELEASE_STATUSES)},
        "frequency_enum": {"passed": set(data["frequency"].dropna().astype(str)).issubset(FREQUENCIES), "detail": sorted(set(data["frequency"].dropna().astype(str)) - FREQUENCIES)},
        "source_urls_complete": {"passed": bool(data["source_url"].fillna("").astype(str).str.strip().ne("").all()), "detail": int(data["source_url"].fillna("").astype(str).str.strip().eq("").sum())},
        "future_rows_are_forecast": {"passed": int((years.gt(today_year) & data["observation_type"].ne("forecast")).sum()) == 0, "detail": int((years.gt(today_year) & data["observation_type"].ne("forecast")).sum())},
        "derived_rows_are_marked": {"passed": int((data["source_status"].astype(str).eq("derived_aligned") & data["processing_level"].ne("derived")).sum()) == 0, "detail": int((data["source_status"].astype(str).eq("derived_aligned") & data["processing_level"].ne("derived")).sum())},
    })
    return checks
