"""Database connection and schema management — Task A2."""

import sqlite3


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection. Sets PRAGMA journal_mode=WAL for file DBs."""
    conn = sqlite3.connect(db_path)
    # WAL mode is meaningful only on real files, but setting it on :memory: is harmless
    conn.execute("PRAGMA journal_mode=WAL")
    conn.commit()
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the candles table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candles (
            symbol    TEXT    NOT NULL,
            timeframe TEXT    NOT NULL,
            open_time INTEGER NOT NULL,
            open      REAL    NOT NULL,
            high      REAL    NOT NULL,
            low       REAL    NOT NULL,
            close     REAL    NOT NULL,
            volume    REAL    NOT NULL,
            PRIMARY KEY (symbol, timeframe, open_time)
        ) WITHOUT ROWID
        """
    )
    conn.commit()
