"""Classify indicators into core, extended and forecast-oriented asset tiers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_clean" / "macro_observations.csv"
MASTER = ROOT / "metadata" / "indicator_master.csv"
OUT = ROOT / "metadata" / "asset_catalog.csv"
SUMMARY = ROOT / "metadata" / "asset_catalog_summary.json"


def main() -> None:
    df = pd.read_csv(DATA, encoding="utf-8-sig", low_memory=False)
    master = pd.read_csv(MASTER, encoding="utf-8-sig", low_memory=False)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    rows = []
    for indicator, group in df.groupby("indicator_code"):
        historical = group[group["observation_type"].eq("historical")]
        forecast = group[group["observation_type"].eq("forecast")]
        raw = group[group["processing_level"].ne("derived")]
        countries = int(historical["country_code"].nunique())
        sources = int(historical["source_organization"].nunique())
        historical_rows = int(historical["value"].notna().sum())
        if historical_rows >= 100 and countries >= 5 and sources >= 2:
            tier = "core"
            reason = "多国、多源且历史观测充足"
        elif historical_rows >= 100 and (countries >= 5 or sources >= 2):
            tier = "extended"
            reason = "具备一定广度或多源能力，仍需增强"
        elif historical_rows > 0:
            tier = "specialized"
            reason = "国家专属或低覆盖指标"
        else:
            tier = "insufficient"
            reason = "缺少有效历史观测"
        rows.append(
            {
                "indicator_code": indicator,
                "indicator_name_zh": group["indicator_name_zh"].dropna().iloc[0],
                "frequency": group["frequency"].dropna().iloc[0],
                "asset_tier": tier,
                "classification_reason": reason,
                "historical_rows": historical_rows,
                "forecast_rows": int(forecast["value"].notna().sum()),
                "raw_standardized_rows": int(raw["value"].notna().sum()),
                "country_count": countries,
                "source_count": sources,
                "start_date": historical["date"].min() if not historical.empty else "",
                "end_date": historical["date"].max() if not historical.empty else "",
            }
        )
    catalog = pd.DataFrame(rows).sort_values(["asset_tier", "country_count", "source_count"], ascending=[True, False, False])
    observed = set(catalog["indicator_code"])
    pending_rows = []
    for item in master[~master["indicator_code"].isin(observed)].itertuples(index=False):
        pending_rows.append(
            {
                "indicator_code": item.indicator_code,
                "indicator_name_zh": item.indicator_name_zh,
                "frequency": item.frequency,
                "asset_tier": "pending",
                "classification_reason": "已登记元数据，尚无通过质量门禁的正式观测",
                "historical_rows": 0, "forecast_rows": 0, "raw_standardized_rows": 0,
                "country_count": 0, "source_count": 0, "start_date": "", "end_date": "",
            }
        )
    if pending_rows:
        catalog = pd.concat([catalog, pd.DataFrame(pending_rows)], ignore_index=True)
    catalog.to_csv(OUT, index=False, encoding="utf-8-sig")
    payload = {
        "registered_indicator_count": int(len(catalog)),
        "observed_indicator_count": int((catalog["asset_tier"] != "pending").sum()),
        "tiers": {key: int(value) for key, value in catalog["asset_tier"].value_counts().items()},
        "rule_version": "2.0.0",
    }
    SUMMARY.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
