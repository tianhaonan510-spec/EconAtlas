# -*- coding: utf-8 -*-
import pandas as pd

from config import DATA_CLEAN


def _status(warning: bool) -> str:
    return "warning" if warning else "ok"


def _coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["indicator_code", "source_organization", "frequency"], dropna=False)
    rows = []
    for keys, group in grouped:
        indicator, source, frequency = keys
        rows.append(
            {
                "indicator_code": indicator,
                "source_organization": source,
                "frequency": frequency,
                "row_count": len(group),
                "country_count": group["country_code"].nunique(),
                "start_date": group["date"].min(),
                "end_date": group["date"].max(),
                "missing_rate": round(float(group["value"].isna().mean()), 4),
                "source_url_missing_count": int(group["source_url"].isna().sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["indicator_code", "source_organization"])


def _consistency_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    key_cols = ["country_code", "indicator_code", "date", "frequency"]
    for keys, group in df.dropna(subset=["value"]).groupby(key_cols):
        if group["source_organization"].nunique() < 2:
            continue

        values = group[["source_organization", "value"]].copy()
        min_value = values["value"].min()
        max_value = values["value"].max()
        mean_abs = values["value"].abs().mean()
        diff = max_value - min_value
        diff_rate = None if mean_abs == 0 else abs(diff) / mean_abs
        rows.append(
            {
                "country_code": keys[0],
                "indicator_code": keys[1],
                "date": keys[2],
                "frequency": keys[3],
                "source_count": group["source_organization"].nunique(),
                "min_value": min_value,
                "max_value": max_value,
                "absolute_diff": diff,
                "relative_diff": diff_rate,
                "status": "warning" if diff_rate is not None and diff_rate > 0.15 else "ok",
            }
        )
    if not rows:
        return pd.DataFrame(columns=["country_code", "indicator_code", "date", "frequency", "source_count"])
    return pd.DataFrame(rows).sort_values(["status", "indicator_code", "country_code", "date"], ascending=[False, True, True, True])


def _outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in df.dropna(subset=["value"]).groupby(["country_code", "indicator_code", "source_organization"]):
        group = group.sort_values("date").copy()
        if len(group) < 5:
            continue
        q1 = group["value"].quantile(0.25)
        q3 = group["value"].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            continue
        lower = q1 - 3 * iqr
        upper = q3 + 3 * iqr
        flagged = group[(group["value"] < lower) | (group["value"] > upper)]
        for _, row in flagged.iterrows():
            rows.append(
                {
                    "country_code": keys[0],
                    "indicator_code": keys[1],
                    "source_organization": keys[2],
                    "date": row["date"],
                    "value": row["value"],
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "status": "warning",
                }
            )
    return pd.DataFrame(rows)


def run_quality_checks() -> pd.DataFrame:
    path = DATA_CLEAN / "macro_observations.csv"
    if not path.exists():
        raise FileNotFoundError(f"Standardized data not found: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df["date"] = df["date"].astype(str)
    df["indicator_code"] = df["indicator_code"].astype(str)
    key_cols = ["country_code", "indicator_code", "date", "source_organization", "source_dataset"]
    checks = [
        {"check_item": "row_count", "value": len(df), "status": "info"},
        {"check_item": "missing_value_count", "value": int(df["value"].isna().sum()), "status": _status(df["value"].isna().any())},
        {"check_item": "duplicate_key_count", "value": int(df.duplicated(key_cols).sum()), "status": _status(df.duplicated(key_cols).any())},
        {"check_item": "missing_source_url_count", "value": int(df["source_url"].isna().sum()), "status": _status(df["source_url"].isna().any())},
        {"check_item": "country_count", "value": int(df["country_code"].nunique()), "status": "info"},
        {"check_item": "indicator_count", "value": int(df["indicator_code"].nunique()), "status": "info"},
        {"check_item": "source_count", "value": int(df["source_organization"].nunique()), "status": "info"},
        {"check_item": "frequency_count", "value": int(df["frequency"].nunique()), "status": "info"},
    ]

    coverage = _coverage_report(df)
    consistency = _consistency_report(df)
    outliers = _outlier_report(df)

    checks.extend(
        [
            {"check_item": "coverage_rows", "value": len(coverage), "status": "info"},
            {
                "check_item": "multi_source_warning_count",
                "value": int((consistency.get("status", pd.Series(dtype=str)) == "warning").sum()),
                "status": _status(not consistency.empty and (consistency["status"] == "warning").any()),
            },
            {"check_item": "outlier_count", "value": len(outliers), "status": _status(len(outliers) > 0)},
        ]
    )

    report = pd.DataFrame(checks)
    report.to_csv(DATA_CLEAN / "quality_report.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(DATA_CLEAN / "quality_coverage_report.csv", index=False, encoding="utf-8-sig")
    consistency.to_csv(DATA_CLEAN / "quality_consistency_report.csv", index=False, encoding="utf-8-sig")
    outliers.to_csv(DATA_CLEAN / "quality_outlier_report.csv", index=False, encoding="utf-8-sig")
    print(f"[Quality] saved reports to: {DATA_CLEAN}")
    return report


if __name__ == "__main__":
    run_quality_checks()

