# -*- coding: utf-8 -*-
"""
Generate semi-automatic indicator alignment candidates for MacroHub.

The output is a review table. Confirmed mappings keep the current trusted
source_mapping.csv result, while candidate scores explain why the mapping is
credible and which items still need manual review.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE_DIR / "data_clean"
METADATA_DIR = BASE_DIR / "metadata"

OBS_PATH = DATA_CLEAN / "macro_observations.csv"
INDICATOR_PATH = METADATA_DIR / "indicator_master.csv"
MAPPING_PATH = METADATA_DIR / "source_mapping.csv"
OUTPUT_PATH = METADATA_DIR / "alignment_candidates.csv"


STOP_WORDS = {
    "the", "and", "of", "in", "to", "for", "as", "at", "by", "current",
    "constant", "annual", "monthly", "daily", "index", "total",
}


def normalize_text(value: object) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(value: object) -> set[str]:
    return {item for item in normalize_text(value).split() if item not in STOP_WORDS}


def text_similarity(left: object, right: object) -> float:
    left_text = normalize_text(left)
    right_text = normalize_text(right)
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def token_similarity(left: object, right: object) -> float:
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def confidence_level(score: float) -> str:
    if score >= 0.85:
        return "高可信"
    if score >= 0.70:
        return "中可信"
    if score >= 0.55:
        return "低可信"
    return "待复核"


def build_source_items(observations: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "source_organization",
        "source_dataset",
        "source_indicator_code",
        "source_indicator_name",
        "indicator_code",
        "unit",
        "frequency",
    ]
    items = observations[cols].drop_duplicates().copy()
    items = items.rename(columns={"source_organization": "source"})
    items["source_indicator_name"] = items["source_indicator_name"].fillna("")
    return items


def score_candidate(source_row: pd.Series, indicator_row: pd.Series) -> tuple[float, str]:
    name_score = max(
        text_similarity(source_row["source_indicator_name"], indicator_row["indicator_name_en"]),
        token_similarity(source_row["source_indicator_name"], indicator_row["indicator_name_en"]),
    )
    code_score = token_similarity(source_row["source_indicator_code"], indicator_row["indicator_code"])
    unit_score = 1.0 if str(source_row["unit"]) == str(indicator_row["unit"]) else 0.0
    freq_score = 1.0 if str(source_row["frequency"]) == str(indicator_row["frequency"]) else 0.0

    score = (
        0.45 * name_score
        + 0.15 * code_score
        + 0.20 * unit_score
        + 0.20 * freq_score
    )
    reasons = []
    if name_score >= 0.45:
        reasons.append("名称/关键词相似")
    if unit_score == 1.0:
        reasons.append("单位一致")
    if freq_score == 1.0:
        reasons.append("频率一致")
    if code_score >= 0.20:
        reasons.append("代码关键词相近")
    if not reasons:
        reasons.append("需人工复核口径")
    return round(score, 4), "、".join(reasons)


def build_candidates() -> pd.DataFrame:
    observations = pd.read_csv(OBS_PATH)
    indicators = pd.read_csv(INDICATOR_PATH)
    mapping = pd.read_csv(MAPPING_PATH)

    source_items = build_source_items(observations)
    current_mapping = {
        (row.source, row.source_dataset, row.source_indicator_code): row.indicator_code
        for row in mapping.itertuples(index=False)
    }
    current_mapping_by_code = {
        (row.source, row.source_indicator_code): row.indicator_code
        for row in mapping.itertuples(index=False)
    }

    rows = []
    for source_row in source_items.itertuples(index=False):
        source_series = pd.Series(source_row._asdict())
        mapping_key = (
            source_series["source"],
            source_series["source_dataset"],
            source_series["source_indicator_code"],
        )
        confirmed_indicator = current_mapping.get(mapping_key)
        if not confirmed_indicator:
            confirmed_indicator = current_mapping_by_code.get(
                (source_series["source"], source_series["source_indicator_code"])
            )

        scored = []
        for indicator_row in indicators.itertuples(index=False):
            indicator_series = pd.Series(indicator_row._asdict())
            score, reason = score_candidate(source_series, indicator_series)
            if indicator_series["indicator_code"] == confirmed_indicator:
                score = max(score, 0.92)
                reason = "已固化映射；" + reason
            scored.append((score, reason, indicator_series))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_reason, best_indicator = scored[0]
        review_status = "已确认" if best_indicator["indicator_code"] == confirmed_indicator else "待人工复核"

        obs_slice = observations[
            (observations["source_organization"] == source_series["source"])
            & (observations["source_dataset"] == source_series["source_dataset"])
            & (observations["source_indicator_code"] == source_series["source_indicator_code"])
        ]

        rows.append(
            {
                "source": source_series["source"],
                "source_dataset": source_series["source_dataset"],
                "source_indicator_code": source_series["source_indicator_code"],
                "source_indicator_name": source_series["source_indicator_name"],
                "current_indicator_code": confirmed_indicator or "",
                "candidate_indicator_code": best_indicator["indicator_code"],
                "candidate_indicator_name_zh": best_indicator["indicator_name_zh"],
                "candidate_indicator_name_en": best_indicator["indicator_name_en"],
                "match_score": best_score,
                "confidence_level": confidence_level(best_score),
                "match_reason": best_reason,
                "review_status": review_status,
                "source_unit": source_series["unit"],
                "candidate_unit": best_indicator["unit"],
                "source_frequency": source_series["frequency"],
                "candidate_frequency": best_indicator["frequency"],
                "country_count": obs_slice["country_code"].nunique(),
                "observation_count": len(obs_slice),
                "start_date": obs_slice["date"].min(),
                "end_date": obs_slice["date"].max(),
            }
        )

    candidate_df = pd.DataFrame(rows)
    candidate_df = candidate_df.sort_values(
        ["review_status", "match_score", "source", "source_indicator_code"],
        ascending=[False, False, True, True],
    )
    return candidate_df


def main() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    candidate_df = build_candidates()
    candidate_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"[Alignment] saved candidates: {OUTPUT_PATH}")
    print(f"[Alignment] rows={len(candidate_df)}")
    print(candidate_df["review_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
