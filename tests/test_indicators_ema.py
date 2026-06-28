"""Tests for signal_engine.indicators.ema — Task B1.

Hand-computed expected values:
  EMA period=3, seed = first value (SMA seed not used here — pandas ewm seeds
  with the first value by default when adjust=False).

  Recurrence: EMA[i] = alpha * price[i] + (1-alpha) * EMA[i-1]
  alpha = 2 / (period + 1)

  Series: [10, 20, 30, 40, 50], period=3  → alpha = 0.5

  EMA[0] = 10
  EMA[1] = 0.5*20 + 0.5*10 = 15.0
  EMA[2] = 0.5*30 + 0.5*15 = 22.5
  EMA[3] = 0.5*40 + 0.5*22.5 = 31.25
  EMA[4] = 0.5*50 + 0.5*31.25 = 40.625
"""

import pandas as pd
import pytest

from signal_engine.indicators import ema


_PRICES = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
_PERIOD = 3
_ALPHA = 2 / (_PERIOD + 1)  # 0.5

# Hand-computed expected values
_EXPECTED = [10.0, 15.0, 22.5, 31.25, 40.625]


class TestEma:
    def test_output_length_equals_input_length(self):
        result = ema(_PRICES, _PERIOD)
        assert len(result) == len(_PRICES)

    def test_first_value_equals_first_price(self):
        """With adjust=False, EMA[0] == prices[0]."""
        result = ema(_PRICES, _PERIOD)
        assert result.iloc[0] == pytest.approx(_EXPECTED[0])

    def test_hand_computed_values(self):
        """All EMA values match the recurrence formula."""
        result = ema(_PRICES, _PERIOD)
        for i, expected in enumerate(_EXPECTED):
            assert result.iloc[i] == pytest.approx(expected, rel=1e-6), (
                f"EMA[{i}] expected {expected}, got {result.iloc[i]}"
            )

    def test_returns_pandas_series(self):
        assert isinstance(ema(_PRICES, _PERIOD), pd.Series)

    def test_no_lookahead(self):
        """
        Appending a future row must NOT change earlier EMA values.
        ema(prices[:k])[k-1] == ema(prices[:k+1])[k-1]
        """
        k = 3  # check index 2 (0-based)
        short = ema(_PRICES.iloc[:k], _PERIOD)
        long_ = ema(_PRICES.iloc[:k + 1], _PERIOD)
        assert short.iloc[-1] == pytest.approx(long_.iloc[k - 1], rel=1e-9)

    def test_single_element_series(self):
        """EMA of a single value equals that value."""
        s = pd.Series([42.0])
        result = ema(s, period=3)
        assert len(result) == 1
        assert result.iloc[0] == pytest.approx(42.0)

    def test_longer_period_smoother(self):
        """
        A longer period EMA reacts more slowly — its value at the last bar
        should be closer to the first price than a short-period EMA.
        """
        rising = pd.Series([float(i) for i in range(1, 21)])  # 1..20
        fast = ema(rising, 3)
        slow = ema(rising, 10)
        # Fast EMA tracks prices more closely → higher final value for rising series
        assert fast.iloc[-1] > slow.iloc[-1]

    def test_index_preserved(self):
        """Output index matches input index."""
        s = pd.Series([1.0, 2.0, 3.0], index=[10, 20, 30])
        result = ema(s, 2)
        assert list(result.index) == [10, 20, 30]
