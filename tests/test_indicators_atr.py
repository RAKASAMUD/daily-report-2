"""Tests for signal_engine.indicators.atr — Task B2.

Hand-computed ATR (Wilder smoothing, period=3):

OHLC fixture (5 bars):
  bar  open   high   low    close
  0    100    110    90     105
  1    105    115    100    110
  2    110    120    105    115
  3    115    125    108    120
  4    120    130    110    125

True Range:
  TR[0] = high[0] - low[0]                = 110 - 90  = 20   (no prev close)
  TR[1] = max(115-100, |115-105|, |100-105|) = max(15,10,5)  = 15
  TR[2] = max(120-105, |120-110|, |105-110|) = max(15,10,5)  = 15
  TR[3] = max(125-108, |125-115|, |108-115|) = max(17,10,7)  = 17
  TR[4] = max(130-110, |130-120|, |110-120|) = max(20,10,10) = 20

Wilder smoothing (alpha = 1/period = 1/3):
  ATR[0]  = TR[0]                              = 20.0
  ATR[1]  = alpha*TR[1] + (1-alpha)*ATR[0]    = (1/3)*15 + (2/3)*20 = 5 + 13.333 = 18.333...
  ATR[2]  = (1/3)*15 + (2/3)*18.333           = 5 + 12.222 = 17.222...
  ATR[3]  = (1/3)*17 + (2/3)*17.222           = 5.667 + 11.481 = 17.148...
  ATR[4]  = (1/3)*20 + (2/3)*17.148           = 6.667 + 11.432 = 18.099...
"""

import pandas as pd
import pytest

from signal_engine.indicators import atr


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

_OHLC = pd.DataFrame({
    "open":  [100.0, 105.0, 110.0, 115.0, 120.0],
    "high":  [110.0, 115.0, 120.0, 125.0, 130.0],
    "low":   [ 90.0, 100.0, 105.0, 108.0, 110.0],
    "close": [105.0, 110.0, 115.0, 120.0, 125.0],
})

_PERIOD = 3
_ALPHA  = 1 / _PERIOD

# Pre-computed ATR values for the fixture above
_ATR0 = 20.0
_ATR1 = _ALPHA * 15 + (1 - _ALPHA) * _ATR0          # ≈ 18.333
_ATR2 = _ALPHA * 15 + (1 - _ALPHA) * _ATR1          # ≈ 17.222
_ATR3 = _ALPHA * 17 + (1 - _ALPHA) * _ATR2          # ≈ 17.148
_ATR4 = _ALPHA * 20 + (1 - _ALPHA) * _ATR3          # ≈ 18.099

_EXPECTED = [_ATR0, _ATR1, _ATR2, _ATR3, _ATR4]


class TestAtr:
    def test_output_length_equals_input_length(self):
        result = atr(_OHLC, _PERIOD)
        assert len(result) == len(_OHLC)

    def test_returns_pandas_series(self):
        assert isinstance(atr(_OHLC, _PERIOD), pd.Series)

    def test_hand_computed_wilder_values(self):
        """All ATR values match the Wilder recurrence formula."""
        result = atr(_OHLC, _PERIOD)
        for i, expected in enumerate(_EXPECTED):
            assert result.iloc[i] == pytest.approx(expected, rel=1e-6), (
                f"ATR[{i}] expected {expected:.6f}, got {result.iloc[i]:.6f}"
            )

    def test_first_value_equals_first_true_range(self):
        """ATR[0] = high[0] - low[0] (no previous close)."""
        result = atr(_OHLC, _PERIOD)
        tr0 = _OHLC["high"].iloc[0] - _OHLC["low"].iloc[0]
        assert result.iloc[0] == pytest.approx(tr0)

    def test_no_lookahead(self):
        """
        Value at index k must not change when future rows are appended.
        atr(df[:k])[k-1] == atr(df[:k+1])[k-1]
        """
        k = 3
        short = atr(_OHLC.iloc[:k].reset_index(drop=True), _PERIOD)
        long_ = atr(_OHLC.iloc[:k + 1].reset_index(drop=True), _PERIOD)
        assert short.iloc[-1] == pytest.approx(long_.iloc[k - 1], rel=1e-9)

    def test_atr_always_positive(self):
        """ATR values must always be strictly positive."""
        result = atr(_OHLC, _PERIOD)
        assert (result > 0).all()

    def test_wider_range_gives_higher_atr(self):
        """Doubling the high-low range roughly doubles the ATR."""
        wide = _OHLC.copy()
        wide["high"] = _OHLC["high"] + 50
        wide["low"]  = _OHLC["low"]  - 50
        result_normal = atr(_OHLC, _PERIOD)
        result_wide   = atr(wide, _PERIOD)
        assert result_wide.iloc[-1] > result_normal.iloc[-1]

    def test_single_row(self):
        """Single-row df: ATR = high - low."""
        df = pd.DataFrame({"open": [100.0], "high": [110.0],
                           "low": [90.0], "close": [105.0]})
        result = atr(df, period=3)
        assert len(result) == 1
        assert result.iloc[0] == pytest.approx(20.0)
