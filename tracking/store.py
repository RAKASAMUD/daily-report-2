"""Outcomes store — Task A1."""

from signal_engine.types import Signal
from tracking.types import Outcome

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS outcomes (
    symbol              TEXT    NOT NULL,
    timeframe           TEXT    NOT NULL,
    strategy            TEXT    NOT NULL,
    bar_open_time       INTEGER NOT NULL,
    status              TEXT    NOT NULL,
    realized_r          REAL    NOT NULL,
    bars_to_resolution  INTEGER NOT NULL,
    resolved_at         INTEGER NOT NULL,
    resolution_price    REAL    NOT NULL,
    PRIMARY KEY (symbol, timeframe, strategy, bar_open_time)
) WITHOUT ROWID
"""

_INSERT_SQL = """
INSERT OR IGNORE INTO outcomes
    (symbol, timeframe, strategy, bar_open_time, status,
     realized_r, bars_to_resolution, resolved_at, resolution_price)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def init_outcomes_schema(conn) -> None:
    """Create the outcomes table if it doesn't exist."""
    conn.execute(_CREATE_SQL)
    conn.commit()


def write_outcome(conn, o: Outcome) -> int:
    """
    INSERT OR IGNORE the outcome.

    Returns 1 if newly inserted, 0 if duplicate.
    """
    cur = conn.execute(
        _INSERT_SQL,
        (
            o.symbol, o.timeframe, o.strategy, o.bar_open_time, o.status,
            o.realized_r, o.bars_to_resolution, o.resolved_at, o.resolution_price,
        ),
    )
    conn.commit()
    return cur.rowcount


def get_pending_signals(conn) -> list[Signal]:
    """
    Return signals that have NO matching outcomes row, ordered by bar_open_time ascending.
    PENDING = no row in outcomes (LEFT JOIN ... WHERE o.bar_open_time IS NULL).
    """
    sql = """
        SELECT s.symbol, s.timeframe, s.strategy, s.bar_open_time, s.direction,
               s.entry, s.tp, s.sl, s.rr, s.reason, s.strength, s.created_at
        FROM signals s
        LEFT JOIN outcomes o
            ON s.symbol        = o.symbol
           AND s.timeframe     = o.timeframe
           AND s.strategy      = o.strategy
           AND s.bar_open_time = o.bar_open_time
        WHERE o.bar_open_time IS NULL
        ORDER BY s.bar_open_time ASC
    """
    rows = conn.execute(sql).fetchall()
    return [
        Signal(
            symbol=row[0], timeframe=row[1], strategy=row[2],
            bar_open_time=row[3], direction=row[4], entry=row[5],
            tp=row[6], sl=row[7], rr=row[8], reason=row[9],
            strength=row[10], created_at=row[11],
        )
        for row in rows
    ]


def get_outcome_rows(conn) -> list[tuple]:
    """
    Return (strategy, timeframe, status, realized_r) tuples for stats aggregation.
    """
    sql = """
        SELECT strategy, timeframe, status, realized_r
        FROM outcomes
        ORDER BY resolved_at ASC
    """
    return conn.execute(sql).fetchall()
