# -*- coding: utf-8 -*-
import argparse
import json
from datetime import datetime

import pandas as pd

from collectors.bis_collector import collect_bis
from collectors.china_official_collector import collect_china_official
from collectors.ecb_collector import collect_ecb
from collectors.eurostat_collector import collect_eurostat
from collectors.fred_collector import collect_fred
from collectors.oecd_collector import collect_oecd
from collectors.worldbank_collector import collect_worldbank
from config import DATA_CLEAN, DATA_RAW, METADATA_DIR
from quality.check_quality import run_quality_checks
from scripts.build_aligned_derived_sources import build_aligned_derived_sources
from standardizer.standardize import standardize_worldbank
from storage.database import init_db


def _align_to_main_schema(main_file, extra_file):
    df_main = pd.read_csv(main_file, encoding="utf-8-sig", low_memory=False)
    if not extra_file.exists():
        print(f"[Merge] skip missing file: {extra_file}")
        return df_main

    df_extra = pd.read_csv(extra_file, encoding="utf-8-sig", low_memory=False)
    for col in df_main.columns:
        if col not in df_extra.columns:
            df_extra[col] = None
    df_extra = df_extra[df_main.columns]
    return pd.concat([df_main, df_extra], ignore_index=True)


def merge_standardized_sources():
    main_file = DATA_CLEAN / "macro_observations.csv"
    if not main_file.exists():
        raise FileNotFoundError(f"Standardized main data not found: {main_file}")

    df_all = _align_to_main_schema(main_file, DATA_RAW / "imf" / "imf_standardized.csv")
    temp_file = DATA_CLEAN / "_macro_observations_with_imf.csv"
    df_all.to_csv(temp_file, index=False, encoding="utf-8-sig")
    extra_files = [
        DATA_RAW / "fred_raw.csv",
        DATA_RAW / "oecd_raw.csv",
        DATA_RAW / "eurostat_raw.csv",
        DATA_RAW / "ecb_raw.csv",
        DATA_RAW / "bis_raw.csv",
        DATA_RAW / "china_official_raw.csv",
        DATA_RAW / "aligned_derived_raw.csv",
    ]
    for extra_file in extra_files:
        df_all = _align_to_main_schema(temp_file, extra_file)
        df_all.to_csv(temp_file, index=False, encoding="utf-8-sig")
    temp_file.unlink(missing_ok=True)

    df_all["indicator_code"] = df_all["indicator_code"].astype("string")
    df_all = df_all[df_all["indicator_code"].notna() & (df_all["indicator_code"].str.strip() != "")].copy()
    df_all["date"] = df_all["date"].astype(str)

    key_cols = ["country_code", "indicator_code", "date", "source_organization", "source_dataset"]
    df_all = df_all.drop_duplicates(subset=key_cols, keep="last")
    df_all = df_all.sort_values(["source_organization", "country_code", "indicator_code", "date"])
    df_all.to_csv(main_file, index=False, encoding="utf-8-sig")
    print(f"[Merge] merged standardized sources: rows={len(df_all)}")
    return df_all


def write_run_manifest():
    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_files": {
            "worldbank_raw": str(DATA_RAW / "worldbank_raw.csv"),
            "imf_standardized": str(DATA_RAW / "imf" / "imf_standardized.csv"),
            "fred_raw": str(DATA_RAW / "fred_raw.csv"),
            "oecd_raw": str(DATA_RAW / "oecd_raw.csv"),
            "eurostat_raw": str(DATA_RAW / "eurostat_raw.csv"),
            "ecb_raw": str(DATA_RAW / "ecb_raw.csv"),
            "bis_raw": str(DATA_RAW / "bis_raw.csv"),
            "china_official_raw": str(DATA_RAW / "china_official_raw.csv"),
            "aligned_derived_raw": str(DATA_RAW / "aligned_derived_raw.csv"),
            "macro_observations": str(DATA_CLEAN / "macro_observations.csv"),
            "macrohub_db": str(DATA_CLEAN / "macrohub.db"),
        },
        "notes": [
            "World Bank requests use local JSON cache unless --force-refresh is set.",
            "FRED requests use local CSV cache unless --force-refresh is set.",
            "OECD requests use local CSV cache unless --force-refresh is set.",
            "Eurostat requests use local JSON cache unless --force-refresh is set.",
            "ECB requests use local CSV cache unless --force-refresh is set.",
            "BIS requests use local CSV cache unless --force-refresh is set.",
            "China official data is imported from local CSV files in data_raw/china_official.",
            "Aligned derived observations transform selected official source series into common standard indicators for cross-source comparison.",
            "IMF WEO is transformed from the local data_raw/imf/imf_weo.csv file.",
        ],
    }
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    out = METADATA_DIR / "run_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Manifest] saved: {out}")


def run_full_pipeline(force_refresh: bool = False, skip_fred: bool = False, skip_extended: bool = False):
    print("Step 1/10: collect World Bank data")
    collect_worldbank(force_refresh=force_refresh)

    print("Step 2/10: standardize World Bank data")
    standardize_worldbank()

    if not skip_fred:
        print("Step 3/10: collect monthly FRED data")
        collect_fred(force_refresh=force_refresh)
    else:
        print("Step 3/10: skip FRED collection")

    if not skip_extended:
        print("Step 4/10: collect OECD monthly CPI data")
        collect_oecd(force_refresh=force_refresh)
        print("Step 5/10: collect Eurostat HICP data")
        collect_eurostat(force_refresh=force_refresh)
        print("Step 6/10: collect ECB daily exchange rate data")
        collect_ecb(force_refresh=force_refresh)
        print("Step 7/10: collect BIS daily exchange rate data")
        collect_bis(force_refresh=force_refresh)
        print("Step 8/10: import China official local data")
        collect_china_official()
    else:
        print("Step 4-8/10: skip OECD/Eurostat/ECB/BIS/China-official collection")

    print("Step 9/13: build aligned derived cross-source observations")
    build_aligned_derived_sources()

    print("Step 10/13: merge all standardized sources")
    merge_standardized_sources()

    print("Step 11/13: run quality checks")
    run_quality_checks()

    print("Step 12/13: initialize SQLite database")
    init_db()

    print("Step 13/13: write run manifest")
    write_run_manifest()

    print("Pipeline complete.")


def run_merge_only():
    build_aligned_derived_sources()
    merge_standardized_sources()
    run_quality_checks()
    init_db()
    write_run_manifest()


def main():
    parser = argparse.ArgumentParser(description="MacroHub data collection, standardization, merge and DB loader")
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--standardize-only", action="store_true")
    parser.add_argument("--fred-only", action="store_true")
    parser.add_argument("--oecd-only", action="store_true")
    parser.add_argument("--eurostat-only", action="store_true")
    parser.add_argument("--ecb-only", action="store_true")
    parser.add_argument("--bis-only", action="store_true")
    parser.add_argument("--china-official-only", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore local source caches and download again")
    parser.add_argument("--skip-fred", action="store_true", help="Skip FRED monthly data collection")
    parser.add_argument("--skip-extended", action="store_true", help="Skip OECD, Eurostat and ECB collection")
    args = parser.parse_args()

    if args.collect_only:
        collect_worldbank(force_refresh=args.force_refresh)
        return
    if args.standardize_only:
        standardize_worldbank()
        return
    if args.fred_only:
        collect_fred(force_refresh=args.force_refresh)
        return
    if args.oecd_only:
        collect_oecd(force_refresh=args.force_refresh)
        return
    if args.eurostat_only:
        collect_eurostat(force_refresh=args.force_refresh)
        return
    if args.ecb_only:
        collect_ecb(force_refresh=args.force_refresh)
        return
    if args.bis_only:
        collect_bis(force_refresh=args.force_refresh)
        return
    if args.china_official_only:
        collect_china_official()
        return
    if args.merge_only:
        run_merge_only()
        return

    run_full_pipeline(force_refresh=args.force_refresh, skip_fred=args.skip_fred, skip_extended=args.skip_extended)


if __name__ == "__main__":
    main()







