# -*- coding: utf-8 -*-
"""Generate auditable source-to-standard indicator alignment candidates.

Unlike the earlier heuristic, the score is independent from the current
mapping.  Unit/frequency/calculation/seasonal-adjustment are hard constraints,
while names, semantic dimensions and overlapping numeric behaviour provide
ranked evidence.  The current registry is shown only for reviewer comparison.
"""

from __future__ import annotations

from difflib import SequenceMatcher
import hashlib
from pathlib import Path
import re

import pandas as pd

from governance.semantic_model import hard_constraints, infer_domain, infer_measure, unit_family


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE_DIR / "data_clean"
METADATA_DIR = BASE_DIR / "metadata"
OBS_PATH = DATA_CLEAN / "macro_observations.csv"
INDICATOR_PATH = METADATA_DIR / "indicator_master.csv"
MAPPING_PATH = METADATA_DIR / "source_mapping.csv"
OUTPUT_PATH = METADATA_DIR / "alignment_candidates.csv"

STOP_WORDS = {"the", "and", "of", "in", "to", "for", "as", "at", "by", "current", "constant", "annual", "monthly", "daily", "index", "total"}


def normalize_text(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(value: object) -> set[str]:
    return {item for item in normalize_text(value).split() if item not in STOP_WORDS}


def lexical_similarity(left: object, right: object) -> float:
    left_text, right_text = normalize_text(left), normalize_text(right)
    if not left_text or not right_text:
        return 0.0
    left_tokens, right_tokens = tokens(left), tokens(right)
    jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens) if left_tokens and right_tokens else 0.0
    return max(jaccard, SequenceMatcher(None, left_text, right_text).ratio())


def confidence_level(score: float, hard_passed: bool) -> str:
    if not hard_passed:
        return "硬约束失败"
    if score >= 0.82:
        return "高可信"
    if score >= 0.68:
        return "中可信"
    if score >= 0.55:
        return "低可信"
    return "待复核"


def build_source_items(observations: pd.DataFrame) -> pd.DataFrame:
    columns = ["source_organization", "source_dataset", "source_indicator_code", "source_indicator_name", "indicator_code", "unit", "frequency", "seasonal_adjustment", "calculation"]
    available = [column for column in columns if column in observations]
    items = observations[available].drop_duplicates().copy().rename(columns={"source_organization": "source"})
    for column in columns:
        target = "source" if column == "source_organization" else column
        if target not in items:
            items[target] = ""
    return items.fillna("")


def numeric_behaviour_score(source_rows: pd.DataFrame, candidate_code: str, observations: pd.DataFrame) -> tuple[float, int, str]:
    comparison = observations[
        observations["indicator_code"].eq(candidate_code)
        & ~(
            observations["source_organization"].eq(source_rows.iloc[0]["source_organization"])
            & observations["source_dataset"].eq(source_rows.iloc[0]["source_dataset"])
            & observations["source_indicator_code"].eq(source_rows.iloc[0]["source_indicator_code"])
        )
    ]
    key = ["country_code", "date"]
    left = source_rows[key + ["value"]].copy().rename(columns={"value": "source_value"})
    right = comparison.groupby(key, as_index=False)["value"].median().rename(columns={"value": "reference_value"})
    overlap = left.merge(right, on=key, how="inner").dropna()
    if len(overlap) < 3:
        return 0.5, len(overlap), "重叠样本不足，数值行为不加分也不扣分"
    if overlap["source_value"].nunique() < 2 or overlap["reference_value"].nunique() < 2:
        correlation = 0.0
    else:
        correlation = overlap["source_value"].corr(overlap["reference_value"])
    correlation_score = max(0.0, float(correlation)) if pd.notna(correlation) else 0.0
    source_scale = overlap["source_value"].abs().median()
    reference_scale = overlap["reference_value"].abs().median()
    if source_scale == 0 and reference_scale == 0:
        scale_score = 1.0
    elif source_scale <= 0 or reference_scale <= 0:
        scale_score = 0.0
    else:
        ratio = max(source_scale, reference_scale) / min(source_scale, reference_scale)
        # Ratio-based monotonic score avoids an additional runtime dependency.
        scale_score = 1.0 / (1.0 + abs(ratio - 1.0))
    score = 0.75 * correlation_score + 0.25 * scale_score
    return round(score, 4), len(overlap), f"重叠{len(overlap)}条，相关系数={correlation_score:.3f}，量级得分={scale_score:.3f}"


def score_candidate(source: pd.Series, target: pd.Series, source_rows: pd.DataFrame, observations: pd.DataFrame) -> dict:
    source_semantic = {
        "unit": source.get("unit"), "frequency": source.get("frequency"),
        "seasonal_adjustment": source.get("seasonal_adjustment"),
        "measure": infer_measure(source.get("calculation"), source.get("unit"), str(source.get("source_indicator_code", ""))),
    }
    target_semantic = {
        "unit": target.get("unit"), "frequency": target.get("frequency"),
        "seasonal_adjustment": target.get("seasonal_adjustment"),
        "measure": target.get("measure") or infer_measure(target.get("calculation"), target.get("unit"), target.get("indicator_code", "")),
    }
    constraints = hard_constraints(source_semantic, target_semantic)
    lexical = lexical_similarity(source.get("source_indicator_name"), target.get("indicator_name_en"))
    code = lexical_similarity(source.get("source_indicator_code"), target.get("indicator_code"))
    source_domain = infer_domain(str(source.get("source_indicator_code", "")), "", str(source.get("source_indicator_name", "")))
    semantic = 1.0 if source_domain == target.get("domain") else 0.35 if source_domain == "other" else 0.0
    unit = 1.0 if unit_family(source.get("unit")) == unit_family(target.get("unit")) else 0.0
    frequency = 1.0 if str(source.get("frequency")) == str(target.get("frequency")) else 0.0
    context = 1.0 if str(source.get("source_indicator_name", "")).strip() else 0.4
    numerical, overlap, numerical_reason = numeric_behaviour_score(source_rows, str(target["indicator_code"]), observations)
    score = 0.25 * lexical + 0.20 * semantic + 0.15 * unit + 0.10 * frequency + 0.20 * numerical + 0.05 * code + 0.05 * context
    if not constraints.passed:
        score = min(score, 0.49)
    reason = f"名称={lexical:.2f}；语义域={semantic:.2f}；单位={unit:.2f}；频率={frequency:.2f}；{numerical_reason}"
    if constraints.violations:
        reason += "；硬约束：" + "、".join(constraints.violations)
    return {"score": round(score, 4), "reason": reason, "hard_passed": constraints.passed, "violations": "、".join(constraints.violations), "overlap": overlap}


def build_candidates() -> pd.DataFrame:
    observations = pd.read_csv(OBS_PATH, encoding="utf-8-sig", low_memory=False)
    observations["value"] = pd.to_numeric(observations["value"], errors="coerce")
    indicators = pd.read_csv(INDICATOR_PATH, encoding="utf-8-sig")
    mapping = pd.read_csv(MAPPING_PATH, encoding="utf-8-sig")
    source_items = build_source_items(observations)
    mapping_exact = {(str(row.source), str(row.source_dataset), str(row.source_indicator_code)): str(row.indicator_code) for row in mapping.itertuples(index=False)}
    mapping_code = {(str(row.source), str(row.source_indicator_code)): str(row.indicator_code) for row in mapping.itertuples(index=False)}
    rows = []
    for source_row in source_items.itertuples(index=False):
        source = pd.Series(source_row._asdict())
        source_slice = observations[
            observations["source_organization"].astype(str).eq(str(source["source"]))
            & observations["source_dataset"].astype(str).eq(str(source["source_dataset"]))
            & observations["source_indicator_code"].astype(str).eq(str(source["source_indicator_code"]))
        ]
        current = mapping_exact.get((str(source["source"]), str(source["source_dataset"]), str(source["source_indicator_code"]))) or mapping_code.get((str(source["source"]), str(source["source_indicator_code"])), "")
        scored = []
        for target_row in indicators.itertuples(index=False):
            target = pd.Series(target_row._asdict())
            evidence = score_candidate(source, target, source_slice, observations)
            scored.append((evidence["score"], target, evidence))
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best, evidence = scored[0]
        alternatives = scored[1:3]
        candidate_id = hashlib.sha256(f"{source['source']}|{source['source_dataset']}|{source['source_indicator_code']}|{best['indicator_code']}".encode("utf-8")).hexdigest()[:16]
        high_automatic = evidence["hard_passed"] and best_score >= 0.82
        matches_registry = str(best["indicator_code"]) == current
        review_status = "已批准" if high_automatic and matches_registry else "待人工复核"
        rows.append({
            "candidate_id": candidate_id,
            "source": source["source"], "source_dataset": source["source_dataset"],
            "source_indicator_code": source["source_indicator_code"], "source_indicator_name": source["source_indicator_name"],
            "current_indicator_code": current, "candidate_indicator_code": best["indicator_code"],
            "candidate_indicator_name_zh": best["indicator_name_zh"], "match_score": best_score,
            "confidence_level": confidence_level(best_score, evidence["hard_passed"]),
            "hard_constraints_passed": evidence["hard_passed"], "constraint_violations": evidence["violations"],
            "match_reason": evidence["reason"], "numeric_overlap_count": evidence["overlap"],
            "review_status": review_status, "registry_matches_candidate": matches_registry,
            "alternative_2_code": alternatives[0][1]["indicator_code"], "alternative_2_score": alternatives[0][0],
            "alternative_3_code": alternatives[1][1]["indicator_code"], "alternative_3_score": alternatives[1][0],
            "source_unit": source["unit"], "candidate_unit": best["unit"],
            "source_frequency": source["frequency"], "candidate_frequency": best["frequency"],
            "country_count": int(source_slice["country_code"].nunique()), "observation_count": int(len(source_slice)),
            "start_date": source_slice["date"].min(), "end_date": source_slice["date"].max(),
            "scoring_version": "hybrid-2.1.0",
        })
    result = pd.DataFrame(rows)
    return result.sort_values(["review_status", "match_score", "source", "source_indicator_code"], ascending=[False, False, True, True])


def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    candidate_df = build_candidates()
    candidate_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"[Alignment] saved candidates: {OUTPUT_PATH}")
    print(f"[Alignment] rows={len(candidate_df)}")
    print(candidate_df["review_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
