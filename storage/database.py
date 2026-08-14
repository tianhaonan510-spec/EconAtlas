# -*- coding: utf-8 -*-
import sqlite3

import pandas as pd

from config import DATA_CLEAN, DB_PATH, METADATA_DIR


METADATA_TABLES = {
    "indicator_master.csv": "indicator_master",
    "country_master.csv": "country_master",
    "source_mapping.csv": "source_mapping",
    "alignment_candidates.csv": "alignment_candidates",
    "mapping_reviews.csv": "mapping_reviews",
    "revision_events.csv": "revision_events",
}


def init_db() -> None:
    csv_path = DATA_CLEAN / "macro_observations.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Standardized data not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("macro_observations", conn, if_exists="replace", index=False)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_macro_query
            ON macro_observations(country_code, indicator_code, frequency, date)
            """
        )
        for filename, table in METADATA_TABLES.items():
            path = METADATA_DIR / filename
            if path.exists():
                metadata = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
                metadata.to_sql(table, conn, if_exists="replace", index=False)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_macro_source_query
            ON macro_observations(country_code, indicator_code, frequency, source_organization, date)
            """
        )
    print(f"[Database] saved: {DB_PATH}, rows={len(df)}")


def query_observations(country: str, indicator: str, start: str = None, end: str = None, frequency: str = None) -> pd.DataFrame:
    params = [country, indicator]
    sql = """
        SELECT * FROM macro_observations
        WHERE country_code = ? AND indicator_code = ?
    """
    if frequency:
        sql += " AND frequency = ?"
        params.append(frequency)
    if start:
        sql += " AND date >= ?"
        params.append(str(start))
    if end:
        sql += " AND date <= ?"
        params.append(str(end))
    sql += " ORDER BY source_organization, date"
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


if __name__ == "__main__":
    init_db()
