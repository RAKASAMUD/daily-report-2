"""Tests for data_layer.pipeline — Task D1: sync_pair (backfill/incremental/gapfill)."""

import pytest

from data_layer.db import connect, init_schema, get_last_open_time, get_candles
from data_layer.binance import BinanceAdapter
from data_layer.pipeline import sync_pair
from data_layer.testkit import FakeExchange, random_walk_candles
from data_layer.config import TIMEFRAME_MS, BACKFILL_DAYS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def _rows_to_ccxt(rows):
    """Convert Row tuples to ccxt list format [[ts,o,h,l,c,v], ...]."""
    return [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]


SYMBOL = "BTC/USDT"
TF = "5m"
TF_MS = TIMEFRAME_MS[TF]
NOW_MS = 1_700_100_000_000  # fixed "now" for all tests


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSyncPair:
    def test_empty_db_uses_backfill_start(self):
        """
        Empty DB → since = now_ms - backfill_days * 86_400_000.
        All returned rows should be written.
        """
        conn = _make_conn()

        # Generate a small set of rows starting at the expected backfill start
        backfill_days = 2
        expected_since = NOW_MS - backfill_days * 86_400_000
        rows = random_walk_candles(expected_since, TF, n=10, seed=1)
        ccxt_rows = _rows_to_ccxt(rows)

        # Set now_ms well past the last candle so none are dropped as unclosed
        last_open = rows[-1][0]
        now_ms = last_open + TF_MS * 2

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)

        inserted = sync_pair(conn, adapter, SYMBOL, TF, now_ms, backfill_days)
        assert inserted == 10

        # Verify all rows landed in the DB
        last = get_last_open_time(conn, SYMBOL, TF)
        assert last == rows[-1][0]

    def test_db_has_data_since_is_last_plus_step(self):
        """
        DB already has data → since = last_open_time + tf_ms (only newer rows fetched).
        """
        conn = _make_conn()
        backfill_days = 2

        # Seed the DB with some initial rows
        seed_rows = random_walk_candles(1_700_000_000_000, TF, n=5, seed=2)
        from data_layer.db import write_candles
        write_candles(conn, SYMBOL, TF, seed_rows)

        # New rows start one step after the last seeded row
        last_seeded = seed_rows[-1][0]
        new_start = last_seeded + TF_MS
        new_rows = random_walk_candles(new_start, TF, n=5, seed=3)
        ccxt_rows = _rows_to_ccxt(new_rows)

        now_ms = new_rows[-1][0] + TF_MS * 2

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)

        inserted = sync_pair(conn, adapter, SYMBOL, TF, now_ms, backfill_days)
        assert inserted == 5

        # DB should now have all 10 rows
        assert get_last_open_time(conn, SYMBOL, TF) == new_rows[-1][0]

    def test_rerun_same_sync_writes_zero_rows(self):
        """Running the same sync twice is idempotent — second run inserts 0."""
        conn = _make_conn()
        backfill_days = 1

        rows = random_walk_candles(1_700_000_000_000, TF, n=8, seed=4)
        ccxt_rows = _rows_to_ccxt(rows)
        now_ms = rows[-1][0] + TF_MS * 2

        # First sync
        fake1 = FakeExchange(pages=[ccxt_rows[:], []])
        adapter1 = BinanceAdapter(fake1)
        sync_pair(conn, adapter1, SYMBOL, TF, now_ms, backfill_days)

        # Second sync returns the same rows → 0 new inserts
        fake2 = FakeExchange(pages=[list(ccxt_rows), []])
        adapter2 = BinanceAdapter(fake2)
        inserted = sync_pair(conn, adapter2, SYMBOL, TF, now_ms, backfill_days)
        assert inserted == 0

    def test_tail_gap_filled_in_one_call(self):
        """
        DB stops several candles before now → gap is filled in one sync_pair call.
        """
        conn = _make_conn()
        backfill_days = 1

        # Seed DB with early rows
        early_rows = random_walk_candles(1_700_000_000_000, TF, n=5, seed=5)
        from data_layer.db import write_candles
        write_candles(conn, SYMBOL, TF, early_rows)

        # Gap: several missing candles, then new rows continue
        last_seeded = early_rows[-1][0]
        gap_start = last_seeded + TF_MS  # first missing
        # Skip 3 candles (the gap), then produce 4 more
        fill_start = gap_start
        fill_rows = random_walk_candles(fill_start, TF, n=7, seed=6)
        ccxt_rows = _rows_to_ccxt(fill_rows)

        now_ms = fill_rows[-1][0] + TF_MS * 2

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)

        inserted = sync_pair(conn, adapter, SYMBOL, TF, now_ms, backfill_days)
        assert inserted == 7

        # All 12 rows (5 seed + 7 fill) should be present
        total = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=?",
            (SYMBOL, TF),
        ).fetchone()[0]
        assert total == 12
