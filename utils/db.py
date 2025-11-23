from sqlalchemy import create_engine

DEFAULT_DB = {
    "user": "app_user",
    "password": "pwd1234",
    "host": "localhost",
    "port": 5432,
    "dbname": "ctrader"
}

trendbars_table = "market_data"

def get_engine(db_config=DEFAULT_DB):
    """Tworzy SQLAlchemy engine dla podanej konfiguracji bazy danych."""
    return create_engine(
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )