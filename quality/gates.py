"""Blocking quality gates for publishing an EconAtlas data snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import DATA_CLEAN, METADATA_DIR
from governance.contracts import evaluate_contracts


OUT_FILE = DATA_CLEAN / "quality_gate.json"


def run_quality_gates(raise_on_failure: bool = True) -> dict:
    data = pd.read_csv(DATA_CLEAN / "macro_observations.csv", encoding="utf-8-sig", low_memory=False)
    master = pd.read_csv(METADATA_DIR / "indicator_master.csv", encoding="utf-8-sig", low_memory=False)
    checks = evaluate_contracts(data, master)
    required_semantic_fields = {"domain", "concept", "measure", "unit_family", "semantic_signature"}
    checks["indicator_semantics_complete"] = {
        "passed": required_semantic_fields.issubset(master.columns),
        "detail": sorted(required_semantic_fields - set(master.columns)),
    }
    mapping_path = METADATA_DIR / "source_mapping.csv"
    mapping = pd.read_csv(mapping_path, encoding="utf-8-sig") if mapping_path.exists() else pd.DataFrame()
    registry_scope = data[data["processing_level"].ne("derived")]
    source_keys = set(zip(registry_scope["source_organization"].astype(str), registry_scope["source_indicator_code"].astype(str)))
    mapping_keys = set(zip(mapping.get("source", pd.Series(dtype=str)).astype(str), mapping.get("source_indicator_code", pd.Series(dtype=str)).astype(str)))
    unmapped = sorted(source_keys - mapping_keys)
    checks["source_series_registered"] = {"passed": not unmapped, "detail": ["|".join(item) for item in unmapped[:50]]}
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
