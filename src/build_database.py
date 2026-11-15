"""
Build the SQLite database used by the City Bike-Share analysis.

Steps
-----
1. Locate the raw CSV files (downloaded from Kaggle with `kagglehub`, or a
   folder you pass with --data-dir).
2. Load the four CSVs into SQLite (the 16M-row trips file is streamed in chunks).
3. Create `trips_clean`: a cleaned, feature-enriched copy of the trips table.

Usage
-----
    python -m src.build_database                      # downloads data via kagglehub
    python -m src.build_database --data-dir path/to/csvs
    python -m src.build_database --rebuild            # drop and rebuild everything
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import time

import pandas as pd

KAGGLE_DATASET = "taweilo/capital-bikeshare-dataset-202005202408"
DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "city_bike_share.db")

SMALL_TABLES = {
    "station_list.csv": "station_list",
    "weather.csv": "weather",
    "usage_frequency.csv": "usage_frequency",
}

# The cleaning rules live in sql/02_data_cleaning.sql (single source of truth)
CLEANING_SQL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "sql", "02_data_cleaning.sql")
with open(CLEANING_SQL_PATH, encoding="utf-8") as _fh:
    CREATE_TRIPS_CLEAN_SQL = _fh.read()


def find_data_dir(data_dir: str | None) -> str:
    if data_dir:
        return data_dir
    import kagglehub  # imported lazily so the module works without it
    return kagglehub.dataset_download(KAGGLE_DATASET)


def table_exists(db: sqlite3.Connection, name: str) -> bool:
    row = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def load_csvs(db: sqlite3.Connection, data_dir: str, chunksize: int = 50_000) -> None:
    for csv_name, table in SMALL_TABLES.items():
        print(f"loading {csv_name} -> {table}")
        pd.read_csv(os.path.join(data_dir, csv_name)).to_sql(table, db, if_exists="replace", index=False)

    print("loading daily_rent_detail.csv -> daily_rent_detail (chunked)")
    path = os.path.join(data_dir, "daily_rent_detail.csv")
    first = True
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        chunk.to_sql("daily_rent_detail", db, if_exists="replace" if first else "append", index=False)
        first = False


def build_trips_clean(db: sqlite3.Connection) -> None:
    print("creating trips_clean (a few minutes on the full dataset)")
    db.executescript(CREATE_TRIPS_CLEAN_SQL)
    db.commit()


def build(data_dir: str | None = None, db_path: str = DEFAULT_DB, rebuild: bool = False) -> str:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    start = time.time()
    db = sqlite3.connect(db_path)
    try:
        if rebuild or not table_exists(db, "daily_rent_detail"):
            load_csvs(db, find_data_dir(data_dir))
        else:
            print("raw tables already present, skipping CSV load (use --rebuild to reload)")
        if rebuild or not table_exists(db, "trips_clean"):
            build_trips_clean(db)
        else:
            print("trips_clean already present, skipping")
        n_raw = db.execute("SELECT COUNT(*) FROM daily_rent_detail").fetchone()[0]
        n_clean = db.execute("SELECT COUNT(*) FROM trips_clean").fetchone()[0]
        print(f"raw trips: {n_raw:,} | clean trips: {n_clean:,} | removed: {n_raw - n_clean:,} "
              f"({(n_raw - n_clean) / max(n_raw, 1):.2%})")
    finally:
        db.close()
    print(f"database ready at {db_path} ({time.time() - start:.0f}s)")
    return db_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", help="folder containing the Kaggle CSV files (default: download)")
    ap.add_argument("--db", default=DEFAULT_DB, help="output SQLite path")
    ap.add_argument("--rebuild", action="store_true", help="drop and rebuild all tables")
    a = ap.parse_args()
    build(a.data_dir, a.db, a.rebuild)
