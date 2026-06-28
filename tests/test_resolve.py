"""Tests for tracking.resolve — Task B1."""

import pytest
import pandas as pd

from signal_engine.types import Signal
from tracking.types import Outcome
from tracking.resolve import resolve

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TF = "1h"
TF_MS = 3_600_000          # 1 hour in ms
BAR_OPEN_TIME = 1_000 * TF_MS  # arbitrary start

ENTRY_TIME = BAR_OPEN_TIME + TF_MS  # trigger bar closes = entry moment
FIVEMIN_MS = 5 * 60 * 1_000         # 5 minutes in ms


def _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0) -> Signal:
    return Signal(
        symbol="BTC/USDT", timeframe=TF, strategy="ema_cross",
        bar_open_time=BAR_OPEN_TIME, direction="long",
        entry=entry, tp=tp, sl=sl, rr=rr,
        reason="cross", strength="high",
        created_at=BAR_OPEN_TIME + 60_000,
    )


def _candles(rows: list[tuple]) -> pd.DataFrame:
    """Build a DataFrame from (open_time, open, high, low, close) tuples."""
    return pd.DataFrame(
        [(r[0], r[1], r[2], r[3], r[4], 1.0) for r in rows],
        columns=["open_time", "open", "high", "low", "close", "volume"],
    )


def _bar(offset_bars: int, high: float, low: float, open_: float = 100.0, close: float = 100.0):
    """Return a 5m candle tuple offset from ENTRY_TIME."""
    t = ENTRY_TIME + offset_bars * FIVEMIN_MS
    return (t, open_, high, low, close)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestResolve:
    def test_tp_touched_first_is_win(self):
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        # Bar 0: normal; Bar 3: hits TP (high >= 110)
        df = _candles([
            _bar(0, high=105.0, low=99.0),
            _bar(1, high=107.0, low=98.0),
            _bar(2, high=111.0, low=99.0),  # TP hit
        ])
        o = resolve(sig, df, timeout_bars=10)
        assert o is not None
        assert o.status == "win"
        assert o.realized_r == pytest.approx(2.0)
        # bar 2 is at ENTRY_TIME + 2*FIVEMIN_MS = 10 minutes into the 1h window
        # bars_to_resolution = (10 min) // (60 min) = 0 complete 1h bars
        assert o.bars_to_resolution == 0
        assert o.resolution_price == 110.0

    def test_sl_touched_first_is_loss(self):
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        df = _candles([
            _bar(0, high=102.0, low=91.0),
            _bar(1, high=101.0, low=89.0),  # SL hit
            _bar(2, high=115.0, low=88.0),
        ])
        o = resolve(sig, df, timeout_bars=10)
        assert o is not None
        assert o.status == "loss"
        assert o.realized_r == pytest.approx(-1.0)
        # bar 1 is at ENTRY_TIME + 1*FIVEMIN_MS = 5 minutes into the 1h window → 0 full 1h bars
        assert o.bars_to_resolution == 0
        assert o.resolution_price == 90.0

    def test_ambiguity_same_candle_both_tp_and_sl_is_loss(self):
        """Candle spans both SL and TP → pessimistic → LOSS."""
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        df = _candles([
            _bar(0, high=115.0, low=85.0),  # both hit
        ])
        o = resolve(sig, df, timeout_bars=10)
        assert o is not None
        assert o.status == "loss"
        assert o.realized_r == pytest.approx(-1.0)

    def test_no_hit_window_elapsed_is_expired(self):
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        timeout_bars = 3
        # Need candles covering past the deadline:
        # deadline = ENTRY_TIME + 3 * TF_MS
        # We need at least one 5m candle with open_time >= deadline
        deadline = ENTRY_TIME + timeout_bars * TF_MS

        rows = []
        # Fill 5m candles from entry to well past deadline (safe range, close = 102)
        t = ENTRY_TIME
        while t <= deadline + FIVEMIN_MS:
            rows.append((t, 100.0, 105.0, 98.0, 102.0))
            t += FIVEMIN_MS

        df = _candles([(r[0], r[2], r[3], r[1], r[4]) for r in rows])
        # Rebuild correctly: (open_time, open, high, low, close)
        df2 = pd.DataFrame(
            [(r[0], 100.0, 105.0, 98.0, 102.0, 1.0) for r in rows],
            columns=["open_time", "open", "high", "low", "close", "volume"],
        )
        o = resolve(sig, df2, timeout_bars=timeout_bars)
        assert o is not None
        assert o.status == "expired"
        assert o.bars_to_resolution == timeout_bars
        # realized_r = min(0.0, (102 - 100) / (100 - 90)) = min(0.0, 0.2) = 0.0
        assert o.realized_r == pytest.approx(0.0)

    def test_no_hit_window_not_elapsed_returns_none(self):
        """Window not yet covered → still PENDING → return None."""
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        # Only 2 bars of 5m, not nearly enough to cover a 10-bar 1h timeout
        df = _candles([
            _bar(0, high=105.0, low=96.0),
            _bar(1, high=104.0, low=97.0),
        ])
        o = resolve(sig, df, timeout_bars=10)
        assert o is None

    def test_no_lookahead_pre_entry_candles_ignored(self):
        """Candles before entry_time must be ignored even if they would hit SL."""
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        timeout_bars = 10
        # Pre-entry candle that would hit SL
        pre_entry_bar = (BAR_OPEN_TIME, 100.0, 105.0, 80.0, 85.0, 1.0)  # low=80 < SL
        # Post-entry candles: no hit, window not elapsed
        post_bars = [
            (ENTRY_TIME + i * FIVEMIN_MS, 100.0, 105.0, 96.0, 102.0, 1.0)
            for i in range(2)
        ]
        all_rows = [pre_entry_bar] + post_bars
        df = pd.DataFrame(all_rows, columns=["open_time", "open", "high", "low", "close", "volume"])
        
        # With only 2 post-entry bars and timeout=10 bars (1h each), window not elapsed
        o = resolve(sig, df, timeout_bars=timeout_bars)
        assert o is None  # Still pending, not a loss

    def test_bars_to_resolution_correct_for_win_on_first_bar(self):
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        df = _candles([
            _bar(0, high=111.0, low=99.0),  # TP hit on very first post-entry bar
        ])
        o = resolve(sig, df, timeout_bars=10)
        assert o is not None
        assert o.status == "win"
        assert o.bars_to_resolution == 0  # 0 signal-tf bars elapsed (hit on first 5m bar of entry bar)

    def test_expired_with_loss_position_has_negative_realized_r(self):
        """When price drifted down at expiry but didn't hit SL, realized_r should be negative."""
        sig = _make_signal(entry=100.0, tp=110.0, sl=90.0, rr=2.0)
        timeout_bars = 2
        deadline = ENTRY_TIME + timeout_bars * TF_MS

        # Close price below entry but above SL (e.g., 95)
        rows = []
        t = ENTRY_TIME
        while t <= deadline + FIVEMIN_MS:
            rows.append((t, 100.0, 102.0, 93.0, 95.0, 1.0))
            t += FIVEMIN_MS

        df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume"])
        o = resolve(sig, df, timeout_bars=timeout_bars)
        assert o is not None
        assert o.status == "expired"
        # realized_r = min(0.0, (95 - 100) / (100 - 90)) = min(0.0, -0.5) = -0.5
        assert o.realized_r == pytest.approx(-0.5)
