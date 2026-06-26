"""Tests for data_layer.db — Task B1: write/read, dedup, resume point."""

import pytest
import pandas as pd

from data_layer.db import connect, init_schema, write_candles, get_last_open_time, get_candles

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Row = tuple  # (open_time, open, high, low, close, volume)


def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def _make_rows(n: int, start_open_time: int = 1_000_000, step: int = 300_000) -> list[Row]:
    """Generate n sequential candle rows starting from start_open_time."""
    rows = []
    for i in range(n):
        t = start_open_time + i * step
        rows.append((t, float(100 + i), float(105 + i), float(95 + i), float(102 + i), float(1000 + i)))
    return rows


# ---------------------------------------------------------------------------
# Tests: write_candles
# ---------------------------------------------------------------------------

class TestWriteCandles:
    def test_returns_number_inserted(self):
        conn = _make_conn()
        rows = _make_rows(5)
        count = write_candles(conn, "BTC/USDT", "5m", rows)
        assert count == 5

    def test_dedup_same_rows_returns_zero(self):
        conn = _make_conn()
        rows = _make_rows(3)
        write_candles(conn, "BTC/USDT", "5m", rows)
        # Insert the exact same rows again — should return 0
        count = write_candles(conn, "BTC/USDT", "5m", rows)
        assert count == 0

    def test_dedup_table_count_unchanged(self):
        conn = _make_conn()
        rows = _make_rows(3)
        write_candles(conn, "BTC/USDT", "5m", rows)
        write_candles(conn, "BTC/USDT", "5m", rows)
        total = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
        assert total == 3

    def test_partial_overlap_only_new_rows_inserted(self):
        conn = _make_conn()
        rows = _make_rows(4)
        write_candles(conn, "BTC/USDT", "5m", rows[:2])
        count = write_candles(conn, "BTC/USDT", "5m", rows)  # 2 already exist
        assert count == 2

    def test_empty_list_returns_zero(self):
        conn = _make_conn()
        count = write_candles(conn, "BTC/USDT", "5m", [])
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: get_last_open_time
# ---------------------------------------------------------------------------

class TestGetLastOpenTime:
    def test_returns_none_when_empty(self):
        conn = _make_conn()
        result = get_last_open_time(conn, "BTC/USDT", "5m")
        assert result is None

    def test_returns_max_open_time(self):
        conn = _make_conn()
        rows = _make_rows(5)
        write_candles(conn, "BTC/USDT", "5m", rows)
        result = get_last_open_time(conn, "BTC/USDT", "5m")
        expected = rows[-1][0]
        assert result == expected

    def test_isolated_per_symbol(self):
        conn = _make_conn()
        btc_rows = _make_rows(3, start_open_time=1_000_000)
        eth_rows = _make_rows(5, start_open_time=2_000_000)
        write_candles(conn, "BTC/USDT", "5m", btc_rows)
        write_candles(conn, "ETH/USDT", "5m", eth_rows)
        # BTC last should not be affected by ETH rows
        btc_last = get_last_open_time(conn, "BTC/USDT", "5m")
        eth_last = get_last_open_time(conn, "ETH/USDT", "5m")
        assert btc_last == btc_rows[-1][0]
        assert eth_last == eth_rows[-1][0]

    def test_isolated_per_timeframe(self):
        conn = _make_conn()
        rows_5m = _make_rows(3, start_open_time=1_000_000, step=300_000)
        rows_1h = _make_rows(3, start_open_time=9_000_000, step=3_600_000)
        write_candles(conn, "BTC/USDT", "5m", rows_5m)
        write_candles(conn, "BTC/USDT", "1h", rows_1h)
        assert get_last_open_time(conn, "BTC/USDT", "5m") == rows_5m[-1][0]
        assert get_last_open_time(conn, "BTC/USDT", "1h") == rows_1h[-1][0]


# ---------------------------------------------------------------------------
# Tests: get_candles
# ---------------------------------------------------------------------------

class TestGetCandles:
    def test_returns_dataframe(self):
        conn = _make_conn()
        rows = _make_rows(5)
        write_candles(conn, "BTC/USDT", "5m", rows)
        df = get_candles(conn, "BTC/USDT", "5m")
        assert isinstance(df, pd.DataFrame)

    def test_columns(self):
        conn = _make_conn()
        rows = _make_rows(5)
        write_candles(conn, "BTC/USDT", "5m", rows)
        df = get_candles(conn, "BTC/USDT", "5m")
        expected_cols = ["open_time", "open", "high", "low", "close", "volume"]
        assert list(df.columns) == expected_cols

    def test_limit_returns_latest_rows(self):
        conn = _make_conn()
        rows = _make_rows(10)
        write_candles(conn, "BTC/USDT", "5m", rows)
        df = get_candles(conn, "BTC/USDT", "5m", limit=3)
        assert len(df) == 3
        # Should be the 3 most recent rows
        expected_times = [r[0] for r in rows[-3:]]
        assert list(df["open_time"]) == expected_times

    def test_ascending_by_open_time(self):
        conn = _make_conn()
        rows = _make_rows(5)
        write_candles(conn, "BTC/USDT", "5m", rows)
        df = get_candles(conn, "BTC/USDT", "5m")
        assert list(df["open_time"]) == sorted(df["open_time"])

    def test_empty_returns_empty_dataframe(self):
        conn = _make_conn()
        df = get_candles(conn, "BTC/USDT", "5m")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_default_limit_500(self):
        conn = _make_conn()
        rows = _make_rows(600)
        write_candles(conn, "BTC/USDT", "5m", rows)
        df = get_candles(conn, "BTC/USDT", "5m")
        assert len(df) == 500
