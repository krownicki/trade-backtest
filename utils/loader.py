#!/usr/bin/env python3
"""
import_csv_postgres.py
Usage: python import_csv_postgres.py path/to/file.csv SYMBOL_ID [--table TABLE] [--dburl DBURL]
Defaults DB connection values match the docker run in the task.
"""
import argparse
from sqlalchemy import create_engine, text
import pandas as pd
import sys

DEFAULT_DB = {
    "user": "app_user",
    "password": "pwd1234",
    "host": "localhost",
    "port": 5432,
    "dbname": "ctrader"
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    id SERIAL PRIMARY KEY,
    symbol_id INTEGER NOT NULL,
    period INTEGER,
    volume BIGINT,
    low DOUBLE PRECISION,
    open DOUBLE PRECISION,
    close DOUBLE PRECISION,
    high DOUBLE PRECISION,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (symbol_id, period, timestamp)
);
"""

def build_db_url(user, password, host, port, dbname):
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

def prepare_df(df, args):
    if "timestamp" not in df.columns:
        print("Plik CSV musi zawierać kolumnę 'timestamp'.", file=sys.stderr)
        sys.exit(1)
    # Optionally compute open/close/high if deltas present and open/close/high missing
    if {"delta_open", "delta_close", "delta_high", "low"}.issubset(df.columns):
        if "open" not in df.columns:
            df["open"] = df["low"] + df["delta_open"]
        if "close" not in df.columns:
            df["close"] = df["low"] + df["delta_close"]
        if "high" not in df.columns:
            df["high"] = df["low"] + df["delta_high"]
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df["symbol_id"] = int(args.symbol_id)

    df = df.drop_duplicates(subset=["period", "symbol_id", "timestamp"], keep="first")
    # Keep only relevant columns (columns present in CSV + computed open/close/high + symbol_id)
    # This prevents to_sql failing if extra columns exist
    allowed = ["symbol_id", "period", "volume", "low", "open", "close", "high", "timestamp"]
    cols = [c for c in allowed if c in df.columns]
    df_to_insert = df[cols].copy()

    return df_to_insert

def save_chunk_in_db(df_chunk, engine, table):
    # znajdz min i max timestmap dla period i symbol_id
    # pobierz timestamp ale odflitruj >= min_timestamp i <= max_timestamp
    # sprawdź których nie ma w bazie danych i tylko te dodaj
    if df_chunk.empty:
        print("Batch pusty, pomijam.")
        return 0, 0

        # assume symbol_id same for whole chunk
    symbol_id = int(df_chunk["symbol_id"].iloc[0])
    has_period = "period" in df_chunk.columns
    period_val = int(df_chunk["period"].iloc[0]) if has_period else None

    # min/max timestamp in chunk
    min_ts = df_chunk["timestamp"].min()
    max_ts = df_chunk["timestamp"].max()

    # fetch existing timestamps from DB only in this range (and for symbol_id and period if available)
    existing_ts = set()
    with engine.begin() as conn:
        if has_period:
            q = text(
                f"SELECT timestamp FROM {table} "
                "WHERE symbol_id = :symbol_id AND period = :period "
                "AND timestamp >= :min_ts AND timestamp <= :max_ts"
            )
            res = conn.execute(q, {"symbol_id": symbol_id, "period": period_val, "min_ts": min_ts, "max_ts": max_ts})
        else:
            q = text(
                f"SELECT timestamp FROM {table} "
                "WHERE symbol_id = :symbol_id "
                "AND timestamp >= :min_ts AND timestamp <= :max_ts"
            )
            res = conn.execute(q, {"symbol_id": symbol_id, "min_ts": min_ts, "max_ts": max_ts})
        existing_ts = {row[0] for row in res.fetchall()}

    # Filter out rows with timestamps already in DB (compare naive datetimes)
    before = len(df_chunk)
    if existing_ts:
        df_new = df_chunk[~df_chunk["timestamp"].isin(existing_ts)].copy()
    else:
        df_new = df_chunk.copy()
    after = len(df_new)
    skipped = before - after

    if after == 0:
        print(f"Batch: wszystkie {before} wierszy istnieją w DB (pominięto {skipped}).")
        return 0, skipped

    # Insert new rows
    try:
        df_new.to_sql(table, engine, if_exists="append", index=False, method="multi")
        print(f"Batch: wstawiono {after} nowych, pominięto {skipped}.")
        return after, skipped
    except Exception as e:
        print("Błąd przy wstawianiu batcha do DB:", e, file=sys.stderr)
        # W razie błędu nie zakładamy wstawienia żadnego wiersza (można rozszerzyć o retry/log)
        return 0, skipped
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="ścieżka do pliku CSV")
    parser.add_argument("symbol_id", type=int, help="symbolId (int) do przypisania do wierszy")
    parser.add_argument("--table", default="market_data", help="nazwa tabeli w DB (domyślnie market_data)")
    parser.add_argument("--dburl", default=None, help="pełny DB URL - jeśli podasz, nadpisze domyślne parametry")
    parser.add_argument("--batch-size", type=int, default=1000, help="rozmiar batcha (domyślnie 1000)")
    args = parser.parse_args()

    # DB url
    if args.dburl:
        db_url = args.dburl
    else:
        db_url = build_db_url(DEFAULT_DB["user"], DEFAULT_DB["password"],
                              DEFAULT_DB["host"], DEFAULT_DB["port"], DEFAULT_DB["dbname"])

    # Read CSV
    total_rows_loaded = 0
    table = args.table
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL.format(table=table)))
    try:
        for chunk in pd.read_csv(args.csv, parse_dates=["timestamp"], chunksize=args.batch_size):
            df = prepare_df(chunk, args)
            save_chunk_in_db(df, engine, table)
            total_rows_loaded += len(df)
    except Exception as e:
        print("Błąd wczytywania CSV:", e, file=sys.stderr)
        sys.exit(1)

    print(f"Załadowano {total_rows_loaded} wierszy")

        # q = text(f"SELECT timestamp FROM {table} WHERE symbol_id = :symbol_id AND period = :period")
        # res = conn.execute(q, {"symbol_id": args.symbol_id, "period": args.period})
        # existing_ts = {row[0] for row in res.fetchall()}

    # Filter out rows with timestamps already in DB
    # before = len(df_to_insert)
    # if existing_ts:
    #     df_new = df_to_insert[~df_to_insert["timestamp"].isin(existing_ts)].copy()
    # else:
    #     df_new = df_to_insert.copy()
    # after = len(df_new)
    # skipped = before - after
    #
    # if after == 0:
    #     print(f"Brak nowych rekordów do dodania (wszystkie {before} rekordów już są w DB).")
    #     return
    #
    # # Insert new rows
    # try:
    #     # to_sql używa SQLAlchemy engine
    #     df_new.to_sql(table, engine, if_exists="append", index=False, method="multi")
    #     print(f"Wstawiono {after} nowych rekordów do tabeli '{table}'. Pominięto {skipped}.")
    # except Exception as e:
    #     print("Błąd przy wstawianiu do DB:", e, file=sys.stderr)
    #     sys.exit(1)

if __name__ == "__main__":
    main()