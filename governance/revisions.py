"""Observation revision tracking between two published snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib

import pandas as pd


KEY_COLUMNS = ["country_code", "indicator_code", "date", "source_organization", "source_dataset"]


def detect_revisions(previous: pd.DataFrame | None, current: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    columns = KEY_COLUMNS + ["previous_value", "new_value", "absolute_change", "previous_data_version", "new_data_version", "detected_at", "event_id"]
    if previous is None or previous.empty or current.empty or not set(KEY_COLUMNS + ["value"]).issubset(previous.columns) or not set(KEY_COLUMNS + ["value"]).issubset(current.columns):
        existing = pd.read_csv(output_path, encoding="utf-8-sig") if output_path.exists() else pd.DataFrame(columns=columns)
        if not output_path.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            existing.to_csv(output_path, index=False, encoding="utf-8-sig")
        return existing
    left_columns = KEY_COLUMNS + ["value"] + (["data_version"] if "data_version" in previous else [])
    right_columns = KEY_COLUMNS + ["value"] + (["data_version"] if "data_version" in current else [])
    merged = previous[left_columns].merge(current[right_columns], on=KEY_COLUMNS, how="inner", suffixes=("_previous", "_new"))
    old_value = pd.to_numeric(merged["value_previous"], errors="coerce")
    new_value = pd.to_numeric(merged["value_new"], errors="coerce")
    changed = merged[(old_value - new_value).abs().gt(1e-12)].copy()
    rows = []
    detected_at = datetime.now().isoformat(timespec="seconds")
    for row in changed.itertuples(index=False):
        payload = {column: getattr(row, column) for column in KEY_COLUMNS}
        previous_value = float(getattr(row, "value_previous"))
        new_value = float(getattr(row, "value_new"))
        fingerprint = "|".join(str(payload[column]) for column in KEY_COLUMNS) + f"|{previous_value}|{new_value}"
        payload.update({
            "previous_value": previous_value,
            "new_value": new_value,
            "absolute_change": abs(new_value - previous_value),
            "previous_data_version": getattr(row, "data_version_previous", ""),
            "new_data_version": getattr(row, "data_version_new", ""),
            "detected_at": detected_at,
            "event_id": hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16],
        })
        rows.append(payload)
    new_events = pd.DataFrame(rows, columns=columns)
    existing = pd.read_csv(output_path, encoding="utf-8-sig") if output_path.exists() else pd.DataFrame(columns=columns)
    result = pd.concat([existing, new_events], ignore_index=True).drop_duplicates("event_id", keep="last") if not new_events.empty else existing
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result
