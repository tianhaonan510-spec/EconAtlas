"""Audit EconAtlas data breadth, depth, completeness, freshness and provenance."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data_clean" / "macro_observations.csv"
INDICATOR_FILE = ROOT / "metadata" / "indicator_master.csv"
OUT_DIR = ROOT / "audit"

CORE_FIELDS = [
    "country_code",
    "indicator_code",
    "date",
    "frequency",
    "unit",
    "value",
    "source_organization",
    "source_dataset",
    "source_indicator_code",
    "source_url",
    "last_updated",
    "retrieved_at",
    "data_version",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def safe_year(value: object) -> float:
    text = str(value)
    year = pd.to_numeric(text[:4], errors="coerce")
    return float(year) if pd.notna(year) else float("nan")


def freshness_days(end_date: object, generated: pd.Timestamp) -> float:
    parsed = pd.to_datetime(str(end_date), errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    generated_day = generated.tz_localize(None).normalize() if generated.tzinfo else generated.normalize()
    parsed_day = parsed.tz_localize(None).normalize() if parsed.tzinfo else parsed.normalize()
    return float((generated_day - parsed_day).days)


def markdown_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for values in frame.itertuples(index=False, name=None):
        rows.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in values) + " |")
    return "\n".join(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = pd.Timestamp.now(tz="Asia/Shanghai")
    all_df = read_csv(DATA_FILE)
    if "observation_type" in all_df.columns:
        forecast_df = all_df[all_df["observation_type"].astype(str).eq("forecast")].copy()
        df = all_df[all_df["observation_type"].astype(str).ne("forecast")].copy()
    else:
        forecast_df = all_df.iloc[0:0].copy()
        df = all_df.copy()
    indicators = read_csv(INDICATOR_FILE)
    df["date"] = df["date"].astype(str)
    df["date_year"] = df["date"].map(safe_year)
    df["valid_value"] = pd.to_numeric(df["value"], errors="coerce").notna()
    current_year = generated.year

    source_rows = []
    for source, group in df.groupby("source_organization", dropna=False):
        valid = group[group["valid_value"]]
        source_rows.append(
            {
                "source_organization": source,
                "row_count": len(group),
                "valid_rows": len(valid),
                "valid_rate": round(float(group["valid_value"].mean()), 4),
                "country_count": int(valid["country_code"].nunique()),
                "indicator_count": int(valid["indicator_code"].nunique()),
                "frequency_count": int(valid["frequency"].nunique()),
                "start_date": valid["date"].min() if not valid.empty else "",
                "end_date": valid["date"].max() if not valid.empty else "",
                "source_url_complete_rate": round(float(group["source_url"].notna().mean()), 4),
            }
        )
    source_df = pd.DataFrame(source_rows).sort_values("valid_rows", ascending=False)

    country_rows = []
    for country, group in df.groupby("country_code"):
        valid = group[group["valid_value"]]
        country_rows.append(
            {
                "country_code": country,
                "country_name_zh": group["country_name_zh"].dropna().iloc[0] if group["country_name_zh"].notna().any() else country,
                "row_count": len(group),
                "valid_rows": len(valid),
                "valid_rate": round(float(group["valid_value"].mean()), 4),
                "indicator_count": int(valid["indicator_code"].nunique()),
                "source_count": int(valid["source_organization"].nunique()),
                "frequency_count": int(valid["frequency"].nunique()),
                "start_year": int(valid["date_year"].min()) if valid["date_year"].notna().any() else None,
                "end_year": int(valid["date_year"].max()) if valid["date_year"].notna().any() else None,
            }
        )
    country_df = pd.DataFrame(country_rows).sort_values(["indicator_count", "valid_rows"], ascending=False)

    indicator_rows = []
    for indicator, group in df.groupby("indicator_code"):
        valid = group[group["valid_value"]]
        meta = indicators[indicators["indicator_code"] == indicator]
        indicator_rows.append(
            {
                "indicator_code": indicator,
                "indicator_name_zh": group["indicator_name_zh"].dropna().iloc[0] if group["indicator_name_zh"].notna().any() else indicator,
                "frequency": group["frequency"].dropna().iloc[0] if group["frequency"].notna().any() else "",
                "unit": group["unit"].dropna().iloc[0] if group["unit"].notna().any() else "",
                "row_count": len(group),
                "valid_rows": len(valid),
                "valid_rate": round(float(group["valid_value"].mean()), 4),
                "country_count": int(valid["country_code"].nunique()),
                "source_count": int(valid["source_organization"].nunique()),
                "start_date": valid["date"].min() if not valid.empty else "",
                "end_date": valid["date"].max() if not valid.empty else "",
                "metadata_registered": not meta.empty,
            }
        )
    indicator_df = pd.DataFrame(indicator_rows).sort_values(["country_count", "valid_rows"], ascending=False)

    coverage = (
        df[df["valid_value"]]
        .pivot_table(index="country_code", columns="indicator_code", values="value", aggfunc="count", fill_value=0)
        .astype(int)
    )

    series_rows = []
    series_keys = ["country_code", "indicator_code", "source_organization", "frequency"]
    for keys, group in df.groupby(series_keys):
        ordered = group.sort_values("date")
        valid = ordered[ordered["valid_value"]]
        series_rows.append(
            {
                **dict(zip(series_keys, keys)),
                "row_count": len(group),
                "valid_rows": len(valid),
                "valid_rate": round(float(group["valid_value"].mean()), 4),
                "start_date": valid["date"].min() if not valid.empty else "",
                "end_date": valid["date"].max() if not valid.empty else "",
                "span_years": round(float(valid["date_year"].max() - valid["date_year"].min()), 1) if valid["date_year"].notna().any() else None,
                "freshness_days": freshness_days(valid["date"].max(), generated) if not valid.empty else None,
            }
        )
    series_df = pd.DataFrame(series_rows).sort_values("valid_rows", ascending=False)

    field_completeness = pd.DataFrame(
        [
            {
                "field": field,
                "non_null_rows": int(df[field].notna().sum()),
                "complete_rate": round(float(df[field].notna().mean()), 4),
            }
            for field in CORE_FIELDS
        ]
    )

    if "processing_level" in df.columns:
        derived_mask = df["processing_level"].astype(str).eq("derived")
    else:
        derived_mask = df["status"].astype(str).str.lower().eq("derived_aligned")
    raw_rows = int((~derived_mask).sum())
    derived_rows = int(derived_mask.sum())
    multi_source_indicators = int((indicator_df["source_count"] >= 2).sum())
    single_country_indicators = int((indicator_df["country_count"] == 1).sum())
    low_volume_sources = int((source_df["valid_rows"] < 100).sum())
    summary = {
        "generated_at": generated.isoformat(),
        "row_count": int(len(df)),
        "valid_value_count": int(df["valid_value"].sum()),
        "missing_value_count": int((~df["valid_value"]).sum()),
        "valid_value_rate": round(float(df["valid_value"].mean()), 4),
        "source_count": int(df["source_organization"].nunique()),
        "country_count": int(df["country_code"].nunique()),
        "indicator_count": int(df["indicator_code"].nunique()),
        "frequency_count": int(df["frequency"].nunique()),
        "series_count": int(df[series_keys].drop_duplicates().shape[0]),
        "raw_rows": raw_rows,
        "derived_aligned_rows": derived_rows,
        "derived_aligned_rate": round(derived_rows / len(df), 4),
        "multi_source_indicator_count": multi_source_indicators,
        "single_country_indicator_count": single_country_indicators,
        "low_volume_source_count": low_volume_sources,
        "duplicate_business_key_count": int(
            df.duplicated(["country_code", "indicator_code", "date", "source_organization", "source_dataset"]).sum()
        ),
        "unregistered_indicator_count": int((~indicator_df["metadata_registered"]).sum()),
        "zero_valid_series_count": int((series_df["valid_rows"] == 0).sum()),
        "future_record_count": int((df["date_year"] > current_year).sum()),
        "future_source_count": int(df.loc[df["date_year"] > current_year, "source_organization"].nunique()),
        "forecast_scenario_count": int(len(forecast_df)),
        "forecast_source_count": int(forecast_df["source_organization"].nunique()) if not forecast_df.empty else 0,
        "status_code_count": int(df["status"].nunique(dropna=True)),
    }

    source_df.to_csv(OUT_DIR / "source_audit.csv", index=False, encoding="utf-8-sig")
    country_df.to_csv(OUT_DIR / "country_audit.csv", index=False, encoding="utf-8-sig")
    indicator_df.to_csv(OUT_DIR / "indicator_audit.csv", index=False, encoding="utf-8-sig")
    series_df.to_csv(OUT_DIR / "series_audit.csv", index=False, encoding="utf-8-sig")
    field_completeness.to_csv(OUT_DIR / "field_completeness.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(OUT_DIR / "country_indicator_matrix.csv", encoding="utf-8-sig")
    series_df[series_df["valid_rows"] == 0].to_csv(OUT_DIR / "zero_valid_series.csv", index=False, encoding="utf-8-sig")
    forecast_columns = [
        "country_code", "indicator_code", "date", "value", "source_organization",
        "source_dataset", "source_status", "release_status", "observation_type",
    ]
    forecast_df[[column for column in forecast_columns if column in forecast_df]].to_csv(
        OUT_DIR / "future_records.csv", index=False, encoding="utf-8-sig"
    )
    semantic_columns = [column for column in ["source_organization", "source_status", "release_status", "observation_type"] if column in all_df]
    all_df.groupby(semantic_columns, dropna=False).size().reset_index(name="row_count").to_csv(
        OUT_DIR / "status_semantics.csv", index=False, encoding="utf-8-sig"
    )
    (OUT_DIR / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    weakest_countries = country_df.sort_values(["indicator_count", "valid_rows"]).head(5)
    weakest_sources = source_df.sort_values("valid_rows").head(5)
    report = [
        "# EconAtlas 2.0 数据资产资格审计",
        "",
        f"生成时间：{generated.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        "## 总体结果",
        "",
        f"- 总记录：{summary['row_count']:,} 条；有效数值：{summary['valid_value_count']:,} 条（{summary['valid_value_rate']:.2%}）。",
        f"- 覆盖：{summary['source_count']} 类来源、{summary['country_count']} 个国家（地区）、{summary['indicator_count']} 个标准指标、{summary['frequency_count']} 类频率。",
        f"- 序列数：{summary['series_count']:,}；多源指标：{summary['multi_source_indicator_count']} 个。",
        f"- 原始/直接标准化记录：{summary['raw_rows']:,}；派生对齐记录：{summary['derived_aligned_rows']:,}（{summary['derived_aligned_rate']:.2%}）。",
        f"- 业务键重复：{summary['duplicate_business_key_count']}；未登记指标：{summary['unregistered_indicator_count']}。",
        "",
        "## 需要优先复核",
        "",
        f"- 仅覆盖单一国家（地区）的指标：{summary['single_country_indicator_count']} 个。",
        f"- 有效记录少于 100 条的来源：{summary['low_volume_source_count']} 个。",
        f"- 完全无有效值的序列：{summary['zero_valid_series_count']} 条，不应计入有效覆盖。",
        f"- 当前数据层中的未来记录：{summary['future_record_count']:,} 条；预测情景层独立保存 {summary['forecast_scenario_count']:,} 条，不与历史实绩混合。",
        "- 数据性质、来源状态和发布状态已经拆分为 `observation_type`、`source_status` 与 `release_status`。",
        "- 完整性不能只用总缺失值衡量，还需结合指标的预期发布频率和适用国家建立预期时间轴。",
        "",
        "### 覆盖较弱的国家（地区）",
        "",
        markdown_table(weakest_countries[["country_code", "country_name_zh", "indicator_count", "source_count", "valid_rows"]]),
        "",
        "### 数据量较少的来源",
        "",
        markdown_table(weakest_sources[["source_organization", "valid_rows", "country_count", "indicator_count", "start_date", "end_date"]]),
        "",
        "## 审计产物",
        "",
        "- `source_audit.csv`：来源真实贡献。",
        "- `country_audit.csv`：国家覆盖广度与深度。",
        "- `indicator_audit.csv`：指标覆盖、时间范围与多源情况。",
        "- `series_audit.csv`：每条数据序列的长度、完整率和新鲜度。",
        "- `country_indicator_matrix.csv`：国家—指标覆盖矩阵。",
        "- `field_completeness.csv`：核心字段完整率。",
        "- `zero_valid_series.csv`：完全没有有效数值的序列。",
        "- `future_records.csv`：需区分预测与历史实绩的未来记录。",
        "- `status_semantics.csv`：各来源状态字段的当前取值。",
    ]
    (OUT_DIR / "DATA_AUDIT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Audit outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
