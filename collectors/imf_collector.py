# -*- coding: utf-8 -*-
"""Transform a local IMF WEO CSV file into MacroHub's standardized long table."""

from datetime import datetime

import pandas as pd

from config import COUNTRIES, DATA_RAW, IMF_WEO_MAPPING, INDICATOR_MAP

RAW_FILE = DATA_RAW / "imf" / "imf_weo.csv"
OUT_FILE = DATA_RAW / "imf" / "imf_standardized.csv"


def clean_value(value, scale=None):
    if pd.isna(value):
        return None

    text = str(value).strip().replace(",", "")
    if text in ["", "n/a", "N/A", "--", "nan", "NaN"]:
        return None

    try:
        number = float(text)
        scale_text = str(scale or "").lower()
        if "billion" in scale_text:
            number *= 1_000_000_000
        elif "million" in scale_text:
            number *= 1_000_000
        return number
    except Exception:
        return None


def extract_country_from_series(series_code):
    try:
        return str(series_code).split(".")[0]
    except Exception:
        return None


def extract_indicator_from_series(series_code):
    try:
        parts = str(series_code).split(".")
        if len(parts) >= 2:
            return parts[1]
        return None
    except Exception:
        return None


def read_imf_weo():
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"IMF source file not found: {RAW_FILE}")

    df = pd.read_csv(RAW_FILE, encoding="utf-8-sig", low_memory=False)
    print(f"[IMF] raw file loaded: shape={df.shape}")
    return df


def transform_imf_weo(df):
    required_cols = ["SERIES_CODE", "COUNTRY", "INDICATOR", "FREQUENCY"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"IMF file missing required column: {col}")

    df["imf_country_iso3"] = df["SERIES_CODE"].apply(extract_country_from_series)
    df["imf_indicator_code"] = df["SERIES_CODE"].apply(extract_indicator_from_series)
    df = df[df["imf_indicator_code"].isin(IMF_WEO_MAPPING.keys())].copy()

    iso3_to_platform = {info["iso3"]: code for code, info in COUNTRIES.items()}
    df["country_code"] = df["imf_country_iso3"].map(iso3_to_platform)
    df = df[df["country_code"].notna()].copy()

    year_cols = [c for c in df.columns if str(c).isdigit()]
    retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for _, row in df.iterrows():
        platform_country = row["country_code"]
        country_info = COUNTRIES.get(platform_country, {})
        imf_indicator_code = row["imf_indicator_code"]
        indicator_code = IMF_WEO_MAPPING.get(imf_indicator_code)
        indicator_meta = INDICATOR_MAP.get(indicator_code, {})

        for year in year_cols:
            rows.append(
                {
                    "series_id": f"{platform_country}.{indicator_code}.IMF",
                    "country_code": platform_country,
                    "country_iso2": country_info.get("iso2", platform_country),
                    "country_iso3": country_info.get("iso3", row["imf_country_iso3"]),
                    "country_name_zh": country_info.get("zh", ""),
                    "country_name_en": country_info.get("en", row.get("COUNTRY", "")),
                    "indicator_code": indicator_code,
                    "indicator_name_zh": indicator_meta.get("indicator_name_zh", row.get("INDICATOR", "")),
                    "indicator_name_en": indicator_meta.get("indicator_name_en", row.get("INDICATOR", "")),
                    "date": str(year),
                    "frequency": "A",
                    "unit": indicator_meta.get("unit", row.get("UNIT", "")),
                    "seasonal_adjustment": indicator_meta.get("seasonal_adjustment", "NSA"),
                    "calculation": indicator_meta.get("calculation", ""),
                    "value": clean_value(row.get(year), row.get("SCALE")),
                    "source_organization": "IMF",
                    "source_dataset": "World Economic Outlook",
                    "source_indicator_code": imf_indicator_code,
                    "source_series_code": row.get("SERIES_CODE", ""),
                    "source_indicator_name": row.get("INDICATOR", ""),
                    "source_url": "https://data.imf.org/en/datasets/IMF.RES:WEO",
                    "last_updated": row.get("UPDATE_DATE", ""),
                    "status": "official",
                    "retrieved_at": retrieved_at,
                    "data_version": str(row.get("UPDATE_DATE", "")) or retrieved_at[:10],
                }
            )

    return pd.DataFrame(rows).sort_values(["country_code", "indicator_code", "date"])


def main():
    df_raw = read_imf_weo()
    df_std = transform_imf_weo(df_raw)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_std.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[IMF] standardized rows={len(df_std)}")
    print(f"[IMF] saved: {OUT_FILE}")


if __name__ == "__main__":
    main()


