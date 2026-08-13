# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from services.query_service import build_batch_response, build_query_response

OUT_FILE = PROJECT_DIR / "data_clean" / "performance_report.csv"
DB_PATH = PROJECT_DIR / "data_clean" / "macrohub.db"
SAMPLE_QUERIES = PROJECT_DIR / "examples" / "sample_queries.json"


def measure(name, func, repeat=30):
    durations = []
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        durations.append((time.perf_counter() - start) * 1000)
    durations_sorted = sorted(durations)
    p95_index = max(0, int(len(durations_sorted) * 0.95) - 1)
    return {
        "scenario": name,
        "repeat": repeat,
        "avg_ms": round(statistics.mean(durations), 3),
        "min_ms": round(min(durations), 3),
        "max_ms": round(max(durations), 3),
        "p95_ms": round(durations_sorted[p95_index], 3),
    }


def metadata_query():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM macro_observations").fetchone()
        cur.execute("SELECT COUNT(DISTINCT source_organization) FROM macro_observations").fetchone()
        cur.execute("SELECT COUNT(DISTINCT indicator_code) FROM macro_observations").fetchone()
        cur.execute("SELECT COUNT(DISTINCT country_code) FROM macro_observations").fetchone()


def load_batch_queries():
    return json.loads(SAMPLE_QUERIES.read_text(encoding="utf-8"))


def main():
    batch_queries = load_batch_queries()
    rows = [
        measure(
            "annual_multi_source_query_us_cpi",
            lambda: build_query_response("US", "CPI_YOY_A", "2020", "2024", "A"),
        ),
        measure(
            "monthly_multi_source_query_de_cpi",
            lambda: build_query_response("DE", "CPI_YOY_M", "2024-01", "2024-12", "M"),
        ),
        measure(
            "daily_bis_query_cn_exchange_rate",
            lambda: build_query_response("CN", "EXCHANGE_RATE_USD_D", "2024-01-02", "2024-01-10", "D", "BIS"),
        ),
        measure("metadata_sql_counts", metadata_query),
        measure("batch_query_sample_file", lambda: build_batch_response(batch_queries), repeat=10),
    ]
    out = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(out.to_string(index=False))
    print(f"saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
