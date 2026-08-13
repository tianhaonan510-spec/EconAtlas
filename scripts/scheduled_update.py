# -*- coding: utf-8 -*-
"""Scheduled MacroHub data update entrypoint.

This script is intended for Windows Task Scheduler or any cron-like runner. It
updates source data, refreshes quality reports and SQLite storage, optionally
runs query benchmarks, and writes a machine-readable status file for the
dashboard.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import DATA_CLEAN, LOG_DIR, METADATA_DIR  # noqa: E402
from main_collect import run_full_pipeline  # noqa: E402

STATUS_FILE = METADATA_DIR / "update_status.json"
UPDATE_LOG = LOG_DIR / "scheduled_update.log"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with UPDATE_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{now_text()}] {message}\n")


def write_status(payload: dict) -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def data_summary() -> dict:
    data_file = DATA_CLEAN / "macro_observations.csv"
    if not data_file.exists():
        return {"data_file_exists": False}
    df = pd.read_csv(data_file, encoding="utf-8-sig")
    return {
        "data_file_exists": True,
        "row_count": int(len(df)),
        "source_count": int(df["source_organization"].nunique()) if "source_organization" in df.columns else 0,
        "indicator_count": int(df["indicator_code"].nunique()) if "indicator_code" in df.columns else 0,
        "country_count": int(df["country_code"].nunique()) if "country_code" in df.columns else 0,
        "frequency_count": int(df["frequency"].nunique()) if "frequency" in df.columns else 0,
    }


def run_benchmark() -> None:
    cmd = [sys.executable, str(PROJECT_DIR / "scripts" / "benchmark_queries.py")]
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, check=False)
    append_log("benchmark stdout: " + result.stdout.strip())
    if result.stderr.strip():
        append_log("benchmark stderr: " + result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f"benchmark failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scheduled MacroHub data update")
    parser.add_argument("--force-refresh", action="store_true", help="Ignore API caches and fetch source data again")
    parser.add_argument("--skip-fred", action="store_true", help="Skip FRED during collection")
    parser.add_argument("--skip-extended", action="store_true", help="Skip OECD/Eurostat/ECB/BIS/China official collection")
    parser.add_argument("--skip-benchmark", action="store_true", help="Skip post-update performance benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Only write a planned status record without changing data")
    args = parser.parse_args()

    started_at = now_text()
    start = time.perf_counter()
    base_status = {
        "status": "running",
        "started_at": started_at,
        "finished_at": "",
        "duration_seconds": None,
        "mode": "force_refresh" if args.force_refresh else "cached_refresh",
        "skip_fred": bool(args.skip_fred),
        "skip_extended": bool(args.skip_extended),
        "skip_benchmark": bool(args.skip_benchmark),
        "message": "Scheduled update is running.",
    }
    write_status(base_status)
    append_log(f"scheduled update started: {base_status}")

    if args.dry_run:
        status = {
            **base_status,
            "status": "dry_run",
            "finished_at": now_text(),
            "duration_seconds": round(time.perf_counter() - start, 3),
            "message": "Dry run completed. No data files were changed.",
            "data_summary": data_summary(),
        }
        write_status(status)
        append_log("dry run completed")
        return 0

    try:
        run_full_pipeline(
            force_refresh=args.force_refresh,
            skip_fred=args.skip_fred,
            skip_extended=args.skip_extended,
        )
        if not args.skip_benchmark:
            run_benchmark()

        summary = data_summary()
        status = {
            **base_status,
            "status": "success",
            "finished_at": now_text(),
            "duration_seconds": round(time.perf_counter() - start, 3),
            "message": "Data update completed successfully.",
            "data_summary": summary,
            "performance_report": str(DATA_CLEAN / "performance_report.csv"),
            "quality_report": str(DATA_CLEAN / "quality_report.csv"),
        }
        write_status(status)
        append_log(f"scheduled update success: {summary}")
        return 0
    except Exception as exc:
        error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        status = {
            **base_status,
            "status": "failed",
            "finished_at": now_text(),
            "duration_seconds": round(time.perf_counter() - start, 3),
            "message": error_text,
            "traceback": traceback.format_exc(),
            "data_summary": data_summary(),
        }
        write_status(status)
        append_log(f"scheduled update failed: {error_text}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
