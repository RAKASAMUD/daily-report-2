"""Database connection, schema, and candle read/write — Tasks A2 + B1."""

import sqlite3

import pandas as pd

# Type alias matching the plan: (open_time, open, high, low, close, volume)
Row = tuple[int, float, float, float, float, float]


# ---------------------------------------------------------------------------
# Task A2: Connection + Schema
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task B1: Write / Read
# ---------------------------------------------------------------------------

def write_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, rows: list[Row]) -> int:
    """
    Insert candle rows for the given symbol/timeframe.

    Uses INSERT OR IGNORE for idempotency (dedup).
    Returns the number of rows actually inserted (0 on duplicates).
    """
    if not rows:
        return 0

    inserted = 0
    for row in rows:
        open_time, open_, high, low, close, volume = row
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO candles
                (symbol, timeframe, open_time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (symbol, timeframe, open_time, open_, high, low, close, volume),
        )
        inserted += cursor.rowcount
    conn.commit()
    return inserted


def get_last_open_time(conn: sqlite3.Connection, symbol: str, timeframe: str) -> int | None:
    """
    Return MAX(open_time) for the given symbol/timeframe pair.
    Returns None if no rows exist yet.
    """
    row = conn.execute(
        "SELECT MAX(open_time) FROM candles WHERE symbol = ? AND timeframe = ?",
        (symbol, timeframe),
    ).fetchone()
    return row[0]  # MAX returns NULL (None in Python) when table is empty


def get_candles(
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    limit: int = 500,
) -> pd.DataFrame:
    """
    Return the most recent `limit` candles for the given symbol/timeframe,
    ordered ascending by open_time.
    Columns: open_time, open, high, low, close, volume.
    """
    rows = conn.execute(
        """
        SELECT open_time, open, high, low, close, volume
        FROM candles
        WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time DESC
        LIMIT ?
        """,
        (symbol, timeframe, limit),
    ).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["open_time", "open", "high", "low", "close", "volume"],
    )
    # Re-sort ascending after DESC fetch (DESC used to get the *latest* N rows)
    if not df.empty:
        df = df.sort_values("open_time").reset_index(drop=True)
    return df
