# pobierz ostatnią znaną datę dla period i symbol_id
# pobierz dane od tej daty do teraz jako csv
# załaduj plik csv do bazy danych
import logging

from sqlalchemy import text, create_engine
from datetime import datetime, timezone

from utils.db import trendbars_table, get_engine
from utils.fetch_prices import fetch_prices
from utils.loader import upload_csv_to_db
import os


def fetch_last_prices(symbol_id, period):
    engine = get_engine()
    latest_ts = get_latest_timestamp(engine, trendbars_table, symbol_id, period)
    now = datetime.now()
    fname = f"{symbol_id}_{period}_tmp.csv"
    if os.path.exists(fname):
        os.remove(fname)
        logging.info(f"Plik {fname} został usunięty.")
    fetch_prices(latest_ts, now, symbol_id, period, fname)
    upload_csv_to_db(engine, fname, symbol_id, trendbars_table)
    if os.path.exists(fname):
        os.remove(fname)
        logging.info(f"Plik {fname} został usunięty po załadowniu do bazy danych!.")




def get_latest_timestamp(engine, table: str, symbol_id: int, period: int):
    query = text(f"""
        SELECT timestamp
        FROM {table}
        WHERE symbol_id = :symbol_id
          AND period = :period
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            "symbol_id": symbol_id,
            "period": period
        }).fetchone()

    return ensure_utc(result[0]) if result else None

def ensure_utc(dt):
    if dt is None:
        return None
    # jeśli datetime nie ma tzinfo, traktujemy go jako UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    # jeśli ma tzinfo, konwertujemy do UTC
    return dt.astimezone(timezone.utc)

if __name__ == "__main__":
    symbol_id = 10019
    fetch_last_prices(symbol_id, 1)
    fetch_last_prices(symbol_id, 7)
    fetch_last_prices(symbol_id, 9)
    fetch_last_prices(symbol_id, 10)