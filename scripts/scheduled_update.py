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
    df = pd.read_csv(data_file, encoding="utf-8-sig", low_memory=False)
    forecast_mask = df.get("observation_type", pd.Series("historical", index=df.index)).astype(str).eq("forecast")
    current = df[~forecast_mask]
    gate_path = DATA_CLEAN / "quality_gate.json"
    try:
        gate_status = json.loads(gate_path.read_text(encoding="utf-8-sig")).get("status", "unknown") if gate_path.exists() else "not_run"
    except Exception:
        gate_status = "unreadable"
    candidates_path = METADATA_DIR / "alignment_candidates.csv"
    candidates = pd.read_csv(candidates_path, encoding="utf-8-sig") if candidates_path.exists() else pd.DataFrame()
    review_pending = int(candidates.get("review_status", pd.Series(dtype=str)).astype(str).eq("待人工复核").sum())
    return {
        "data_file_exists": True,
        "row_count": int(len(df)),
        "current_row_count": int(len(current)),
        "forecast_row_count": int(forecast_mask.sum()),
        "source_count": int(current["source_organization"].nunique()) if "source_organization" in current.columns else 0,
        "indicator_count": int(current["indicator_code"].nunique()) if "indicator_code" in current.columns else 0,
        "country_count": int(current["country_code"].nunique()) if "country_code" in current.columns else 0,
        "frequency_count": int(current["frequency"].nunique()) if "frequency" in current.columns else 0,
        "quality_gate": gate_status,
        "alignment_review_pending": review_pending,
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
