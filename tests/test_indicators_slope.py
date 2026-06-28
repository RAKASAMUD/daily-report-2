"""Tests for ema_slope_falling — Develop 2 Task A2."""

import pandas as pd
from signal_engine.indicators import ema_slope_falling


class TestEmaSlopeFalling:
    def test_falling(self):
        # Current (-1) is 10, lookback 2 bars ago (-1 - 2 = -3) is 12
        series = pd.Series([15.0, 14.0, 12.0, 11.0, 10.0])
        assert ema_slope_falling(series, lookback=2) is True

    def test_rising(self):
        series = pd.Series([10.0, 11.0, 12.0, 14.0, 15.0])
        assert ema_slope_falling(series, lookback=2) is False

    def test_flat(self):
        series = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
        assert ema_slope_falling(series, lookback=2) is False

    def test_not_enough_data(self):
        # Length 2, lookback 2 -> -1 - 2 = -3 (out of bounds for length 2)
        # Should return False safely
        series = pd.Series([10.0, 9.0])
        assert ema_slope_falling(series, lookback=2) is False
