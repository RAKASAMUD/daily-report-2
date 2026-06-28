"""Signal store — Task A1.

Handles schema creation, writing (INSERT OR IGNORE), and reading signals
from the same SQLite DB used by Stage 1 (data_layer).
"""

from signal_engine.types import Signal

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    symbol        TEXT    NOT NULL,
    timeframe     TEXT    NOT NULL,
    strategy      TEXT    NOT NULL,
    bar_open_time INTEGER NOT NULL,
    direction     TEXT    NOT NULL,
    entry         REAL    NOT NULL,
    tp            REAL    NOT NULL,
    sl            REAL    NOT NULL,
    rr            REAL    NOT NULL,
    reason        TEXT    NOT NULL,
    created_at    INTEGER NOT NULL,
    PRIMARY KEY (symbol, timeframe, strategy, bar_open_time)
) WITHOUT ROWID
"""

_INSERT_SQL = """
INSERT OR IGNORE INTO signals
    (symbol, timeframe, strategy, bar_open_time, direction,
     entry, tp, sl, rr, reason, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def init_signals_schema(conn) -> None:
    """Create the signals table if it doesn't exist."""
    conn.execute(_CREATE_SQL)
    conn.commit()


def write_signal(conn, sig: Signal) -> int:
    """
    INSERT OR IGNORE the signal.

    Returns 1 if the row was newly inserted, 0 if it already existed (dedup).
    """
    cur = conn.execute(
        _INSERT_SQL,
        (
            sig.symbol, sig.timeframe, sig.strategy, sig.bar_open_time,
            sig.direction, sig.entry, sig.tp, sig.sl, sig.rr,
            sig.reason, sig.created_at,
        ),
    )
    conn.commit()
    return cur.rowcount  # 1 if inserted, 0 if ignored


def get_signals(
    conn,
    symbol: str | None = None,
    timeframe: str | None = None,
    strategy: str | None = None,
    limit: int = 100,
) -> list[Signal]:
    """
    Return the most recent `limit` signals, ascending by bar_open_time.

    Optional filters: symbol, timeframe, strategy.
    """
    conditions: list[str] = []
    params: list = []

    if symbol is not None:
        conditions.append("symbol = ?")
        params.append(symbol)
    if timeframe is not None:
        conditions.append("timeframe = ?")
        params.append(timeframe)
    if strategy is not None:
        conditions.append("strategy = ?")
        params.append(strategy)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Fetch the `limit` most recent rows (DESC), then flip to ASC for output
    sql = f"""
        SELECT symbol, timeframe, strategy, bar_open_time, direction,
               entry, tp, sl, rr, reason, created_at
        FROM (
            SELECT * FROM signals {where}
            ORDER BY bar_open_time DESC
            LIMIT ?
        )
        ORDER BY bar_open_time ASC
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()

    return [
        Signal(
            symbol=row[0],
            timeframe=row[1],
            strategy=row[2],
            bar_open_time=row[3],
            direction=row[4],
            entry=row[5],
            tp=row[6],
            sl=row[7],
            rr=row[8],
            reason=row[9],
            created_at=row[10],
        )
        for row in rows
    ]
