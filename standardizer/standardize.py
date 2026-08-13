from datetime import datetime
import pandas as pd

from config import DATA_RAW, DATA_CLEAN, METADATA_DIR, INDICATOR_MAP, COUNTRIES

DATA_CLEAN.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

def build_indicator_master() -> pd.DataFrame:
    rows = []
    for code, meta in INDICATOR_MAP.items():
        rows.append({
            "indicator_code": code,
            "indicator_name_zh": meta["indicator_name_zh"],
            "indicator_name_en": meta["indicator_name_en"],
            "unit": meta["unit"],
            "frequency": meta["frequency"],
            "seasonal_adjustment": meta["seasonal_adjustment"],
            "calculation": meta["calculation"],
            "source_count": len(meta.get("sources", [])),
        })
    df = pd.DataFrame(rows)
    df.to_csv(METADATA_DIR / "indicator_master.csv", index=False, encoding="utf-8-sig")
    return df

def build_source_mapping() -> pd.DataFrame:
    rows = []
    for code, meta in INDICATOR_MAP.items():
        for src in meta["sources"]:
            rows.append({
                "source": src["organization"],
                "source_dataset": src["dataset"],
                "source_indicator_code": src["source_series_code"],
                "indicator_code": code,
            })
    df = pd.DataFrame(rows)
    df.to_csv(METADATA_DIR / "source_mapping.csv", index=False, encoding="utf-8-sig")
    return df

def build_country_master() -> pd.DataFrame:
    rows = []
    for k, v in COUNTRIES.items():
        rows.append({
            "country_code": k,
            "country_iso2": v["iso2"],
            "country_iso3": v["iso3"],
            "country_name_zh": v["zh"],
            "country_name_en": v["en"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(METADATA_DIR / "country_master.csv", index=False, encoding="utf-8-sig")
    return df

def standardize_worldbank() -> pd.DataFrame:
    raw_path = DATA_RAW / "worldbank_raw.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"未找到原始数据：{raw_path}，请先运行 python main_collect.py --collect-only")
    raw = pd.read_csv(raw_path)
    indicator_master = build_indicator_master()
    source_mapping = build_source_mapping()
    country_master = build_country_master()
    df = raw.merge(source_mapping, on=["source_indicator_code", "source_dataset"], how="left")
    df = df[df["indicator_code"].notna()].copy()
    df = df.merge(indicator_master, on="indicator_code", how="left")
    df = df.merge(country_master, on="country_code", how="left")
    df["date"] = df["date"].astype(str)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["series_id"] = df["country_code"] + "." + df["indicator_code"]
    if "last_updated" not in df.columns:
        df["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    cols = [
        "series_id", "country_code", "country_iso2", "country_iso3", "country_name_zh", "country_name_en",
        "indicator_code", "indicator_name_zh", "indicator_name_en", "date", "frequency", "unit",
        "seasonal_adjustment", "calculation", "value", "source_organization", "source_dataset",
        "source_indicator_code", "source_indicator_name", "source_url", "last_updated", "status", "retrieved_at",
        "data_version"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].sort_values(["country_code", "indicator_code", "date"])
    out = DATA_CLEAN / "macro_observations.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[Standardize] saved: {out}, shape={df.shape}")
    return df

if __name__ == "__main__":
    standardize_worldbank()

