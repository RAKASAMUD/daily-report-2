"""Tests for signal_engine.strategies.ema_cross — Task C2.

All test series are engineered so the answer is known exactly.
No network access — pure unit tests.

Mathematical foundations:
-----------------------------------------------------------------------
Series A — FLAT then SPIKE (10 bars at 10, last bar at 100):
  [10]*10 + [100]  →  fresh cross at last bar (fast reacts faster to spike)

  With fast=3, slow=5, alpha_fast=0.5, alpha_slow=2/6:
    EMA3[9] ≈ 10.0,  EMA5[9] ≈ 10.0   (both converged)
    EMA3[10] = 0.5*100 + 0.5*10 = 55.0
    EMA5[10] = (2/6)*100 + (4/6)*10 = 40.0
    → fast[-1]=55 > slow[-1]=40  ✓
    → fast[-2]=10 <= slow[-2]=10 ✓  FRESH CROSS

Series B — already crossed (two spikes, cross happened one bar ago):
  [10]*10 + [80, 100]
    Bar -2 (close=80): EMA3=45 > EMA5=33.33  (cross at bar -2)
    Bar -1 (close=100): EMA3=72.5 > EMA5=55.56
    → fast[-2]=45 > slow[-2]=33.33  NOT a fresh cross → None

Series C — trend filter scenario (long history + deep drop + small recovery):
  [1000]*50 + [100]*8 + [250]  with fast=2, slow=3, trend=10
    After 50 bars at 1000: all EMAs ≈ 1000
    After 8 bars at 100 (alpha2=2/3):   EMA2[-1] ≈ 100.14
    After 8 bars at 100 (alpha3=0.5):   EMA3[-1] ≈ 103.52
    After 8 bars at 100 (alpha10=2/11): EMA10[-1] ≈ 279.84

    Last bar (close=250):
      EMA2[last] = (2/3)*250 + (1/3)*100.14 ≈ 200.05
      EMA3[last] = 0.5*250 + 0.5*103.52    ≈ 176.76
      EMA10[last]= (2/11)*250+(9/11)*279.84≈ 274.41

    → fast[-1]=200 > slow[-1]=176  ✓  fresh cross ✓
    → close[-1]=250 < EMA10[-1]=274.41 ✓  TREND FILTER triggers → None
    → with use_trend_filter=False → Signal returned ✓
-----------------------------------------------------------------------
"""

import time
import pandas as pd
import pytest

from signal_engine.strategies.ema_cross import ema_cross, cross_strength
from signal_engine.indicators import atr as atr_fn
from signal_engine.types import Signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlc(prices: list[float], start_ms: int = 1_700_000_000_000,
               step_ms: int = 300_000) -> pd.DataFrame:
    """Build a minimal OHLC DataFrame from a list of close prices.

    high = close * 1.01, low = close * 0.99, open = close.
    """
    n = len(prices)
    return pd.DataFrame({
        "open_time": [start_ms + i * step_ms for i in range(n)],
        "open":   [float(p) for p in prices],
        "high":   [float(p) * 1.01 for p in prices],
        "low":    [float(p) * 0.99 for p in prices],
        "close":  [float(p) for p in prices],
        "volume": [1_000.0] * n,
    })


# Base params — small periods so tests stay fast and deterministic
_BASE_PARAMS = {
    "fast": 3,
    "slow": 5,
    "trend": 200,
    "use_trend_filter": False,   # off by default in most tests
    "atr_period": 3,
    "atr_mult": 1.5,
    "rr": 2.0,
    "gap_med": 1.0,
    "gap_high": 2.0,
    "trend_med": 2.0,
    "trend_high": 4.0,
    "symbol": "BTC/USDT",
    "timeframe": "5m",
    "created_at": 1_700_000_999_000,
}

# Series A: flat then spike → fresh cross at last bar
_SERIES_A = [10.0] * 10 + [100.0]

# Series B: two spikes → cross already happened one bar ago → no fresh cross
_SERIES_B = [10.0] * 10 + [80.0, 100.0]

# Series C: long history → deep drop → small recovery (for trend filter)
_SERIES_C = [1000.0] * 50 + [100.0] * 8 + [250.0]


# ---------------------------------------------------------------------------
# Tests: fresh cross
# ---------------------------------------------------------------------------

class TestEmaCrossSignal:
    def test_fresh_cross_at_last_bar_returns_signal(self):
        """A series engineered to cross at the last bar produces a Signal."""
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert isinstance(sig, Signal)

    def test_truncated_one_bar_earlier_returns_none(self):
        """
        Same series minus the spike (cross not yet happened) → None.
        Verifies the signal fires *at* the transition bar.
        """
        df = _make_ohlc(_SERIES_A[:-1])   # drop the spike
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig is None

    def test_already_above_no_fresh_cross_returns_none(self):
        """
        fast was already above slow two bars ago (no fresh cross) → None.
        Verifies once-per-transition semantics.
        """
        df = _make_ohlc(_SERIES_B)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig is None


# ---------------------------------------------------------------------------
# Tests: trend filter
# ---------------------------------------------------------------------------

class TestEmaCrossTrendFilter:
    _FILTER_PARAMS = {
        **_BASE_PARAMS,
        "fast": 2,
        "slow": 3,
        "trend": 10,
    }

    def test_filter_on_close_below_trend_returns_none(self):
        """
        Trend filter ON and close < EMA_trend → None, even though cross exists.
        """
        params = {**self._FILTER_PARAMS, "use_trend_filter": True}
        df = _make_ohlc(_SERIES_C)
        sig = ema_cross(df, params)
        assert sig is None

    def test_filter_off_returns_signal(self):
        """Same data with filter OFF → Signal returned."""
        params = {**self._FILTER_PARAMS, "use_trend_filter": False}
        df = _make_ohlc(_SERIES_C)
        sig = ema_cross(df, params)
        assert isinstance(sig, Signal)


# ---------------------------------------------------------------------------
# Tests: returned Signal fields
# ---------------------------------------------------------------------------

class TestEmaCrossFields:
    def test_direction_is_long(self):
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.direction == "long"

    def test_strategy_name(self):
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.strategy == "ema_cross"

    def test_bar_open_time_is_last_bar(self):
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.bar_open_time == int(df["open_time"].iloc[-1])

    def test_entry_equals_last_close(self):
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.entry == pytest.approx(df["close"].iloc[-1])

    def test_sl_tp_formula(self):
        """sl = entry - atr_mult*ATR;  tp = entry + rr*(entry-sl)."""
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)

        atrv = atr_fn(df, _BASE_PARAMS["atr_period"]).iloc[-1]
        expected_sl = sig.entry - _BASE_PARAMS["atr_mult"] * atrv
        expected_tp = sig.entry + _BASE_PARAMS["rr"] * (sig.entry - expected_sl)

        assert sig.sl == pytest.approx(expected_sl, rel=1e-6)
        assert sig.tp == pytest.approx(expected_tp, rel=1e-6)

    def test_rr_equals_params_rr(self):
        """Effective RR must equal params['rr'] exactly by construction."""
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.rr == pytest.approx(_BASE_PARAMS["rr"], rel=1e-9)

    def test_reason_contains_ema_periods(self):
        """reason mentions the fast and slow EMA periods."""
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert str(_BASE_PARAMS["fast"]) in sig.reason
        assert str(_BASE_PARAMS["slow"]) in sig.reason

    def test_symbol_and_timeframe_from_params(self):
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.symbol == _BASE_PARAMS["symbol"]
        assert sig.timeframe == _BASE_PARAMS["timeframe"]

    def test_strength_is_populated(self):
        """Signal must have a valid strength string."""
        df = _make_ohlc(_SERIES_A)
        sig = ema_cross(df, _BASE_PARAMS)
        assert sig.strength in ("low", "med", "high")


# ---------------------------------------------------------------------------
# Tests: cross_strength helper
# ---------------------------------------------------------------------------

class TestCrossStrength:
    def test_high_strength(self):
        # gap >= 2.0 AND trend >= 4.0 -> high
        assert cross_strength(2.5, 4.5, _BASE_PARAMS) == "high"
        # Only gap high, trend low
        assert cross_strength(2.5, 1.0, _BASE_PARAMS) == "high"

    def test_med_strength(self):
        # gap >= 1.0 AND < 2.0
        assert cross_strength(1.5, 1.0, _BASE_PARAMS) == "med"
        # gap is low, but trend is med (>= 2.0)
        assert cross_strength(0.5, 3.0, _BASE_PARAMS) == "med"

    def test_low_strength(self):
        # both gap and trend are below med thresholds
        assert cross_strength(0.5, 1.0, _BASE_PARAMS) == "low"



# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

class TestEmaCrossEdge:
    def test_too_few_rows_returns_none(self):
        """Less than 3 rows → None, no crash."""
        df = _make_ohlc([100.0, 101.0])
        assert ema_cross(df, _BASE_PARAMS) is None

    def test_single_row_returns_none(self):
        df = _make_ohlc([100.0])
        assert ema_cross(df, _BASE_PARAMS) is None

    def test_does_not_mutate_df(self):
        """Strategy must not mutate the input DataFrame."""
        df = _make_ohlc(_SERIES_A)
        df_copy = df.copy(deep=True)
        ema_cross(df, _BASE_PARAMS)
        pd.testing.assert_frame_equal(df, df_copy)
