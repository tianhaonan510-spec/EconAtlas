from __future__ import annotations

import sqlite3
from typing import Any, Optional

import pandas as pd

from config import DB_PATH


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return value


def _date_filter(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def read_sql(query: str, params: Optional[list[Any]] = None) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params or [])


def query_observations(
    country: str,
    indicator: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    frequency: Optional[str] = None,
    source: Optional[str] = None,
) -> pd.DataFrame:
    sql = """
        SELECT *
        FROM macro_observations
        WHERE country_code = ?
          AND indicator_code = ?
    """
    params: list[Any] = [country, indicator]

    if frequency:
        sql += " AND frequency = ?"
        params.append(frequency)
    if source:
        sql += " AND source_organization = ?"
        params.append(source)

    start_value = _date_filter(start)
    end_value = _date_filter(end)
    if start_value:
        sql += " AND date >= ?"
        params.append(start_value)
    if end_value:
        sql += " AND date <= ?"
        params.append(end_value)

    sql += " ORDER BY source_organization, source_dataset, source_indicator_code, date"
    return read_sql(sql, params)


def _series_from_group(group: pd.DataFrame) -> dict[str, Any]:
    first = group.iloc[0].to_dict()
    observations = []
    for _, row in group.iterrows():
        observations.append(
            {
                "date": str(row.get("date")),
                "value": _clean_value(row.get("value")),
                "status": row.get("status") or "final",
                "retrieved_at": _clean_value(row.get("retrieved_at")),
                "data_version": _clean_value(row.get("data_version")),
            }
        )

    return {
        "series_id": first.get("series_id"),
        "indicator_code": first.get("indicator_code"),
        "indicator_name_zh": first.get("indicator_name_zh"),
        "indicator_name_en": first.get("indicator_name_en"),
        "country_name_zh": first.get("country_name_zh"),
        "country_name_en": first.get("country_name_en"),
        "country_code": first.get("country_code"),
        "frequency": first.get("frequency"),
        "unit": first.get("unit"),
        "seasonal_adjustment": first.get("seasonal_adjustment"),
        "calculation": first.get("calculation"),
        "source": {
            "organization": first.get("source_organization"),
            "dataset": first.get("source_dataset"),
            "source_series_code": first.get("source_indicator_code"),
            "source_url": first.get("source_url"),
        },
        "last_updated": first.get("last_updated"),
        "observations": observations,
    }


def build_query_response(
    country: str,
    indicator: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    frequency: Optional[str] = None,
    source: Optional[str] = None,
) -> dict[str, Any]:
    request_obj = {
        "country": country,
        "indicator_code": indicator,
        "start_date": start,
        "end_date": end,
        "frequency": frequency,
        "source": source,
    }

    df = query_observations(country, indicator, start, end, frequency, source)
    if df.empty:
        return {"request": request_obj, "series": None, "error": {"message": "No data found"}}

    group_cols = ["source_organization", "source_dataset", "source_indicator_code"]
    series_list = [_series_from_group(g) for _, g in df.groupby(group_cols, dropna=False, sort=True)]

    if len(series_list) == 1:
        return {
            "request": request_obj,
            "series": series_list[0],
            "series_count": 1,
            "error": None,
        }

    return {
        "request": request_obj,
        "series": series_list,
        "series_count": len(series_list),
        "error": None,
    }


def build_batch_response(queries: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for index, item in enumerate(queries):
        try:
            results.append(
                build_query_response(
                    country=item["country"],
                    indicator=item["indicator"],
                    start=item.get("start"),
                    end=item.get("end"),
                    frequency=item.get("frequency"),
                    source=item.get("source"),
                )
            )
        except Exception as exc:
            results.append(
                {
                    "request": {"index": index, **item},
                    "series": None,
                    "error": {"message": str(exc)},
                }
            )

    return {
        "request_count": len(queries),
        "success_count": sum(1 for item in results if item.get("error") is None),
        "results": results,
    }
