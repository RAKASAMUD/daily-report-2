"""Tests for Bollinger Bands — Develop 2 Task A1."""

import pandas as pd
import numpy as np
import pytest

from signal_engine.indicators import bollinger_bands


class TestBollingerBands:
    def test_basic_values(self):
        # 5 values, period 3
        series = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])
        mid, upper, lower = bollinger_bands(series, period=3, num_std=2.0)
        
        assert len(mid) == 5
        assert len(upper) == 5
        assert len(lower) == 5
        
        # First 2 values should be NaN because period is 3
        assert np.isnan(mid.iloc[0])
        assert np.isnan(mid.iloc[1])
        
        # Third value (index 2): SMA of [10, 12, 14] = 12
        assert mid.iloc[2] == pytest.approx(12.0)
        # std (ddof=0) of [10, 12, 14]: mean=12, var=((10-12)^2 + (12-12)^2 + (14-12)^2)/3 = 8/3
        std_val = np.sqrt(8/3)
        assert upper.iloc[2] == pytest.approx(12.0 + 2.0 * std_val)
        assert lower.iloc[2] == pytest.approx(12.0 - 2.0 * std_val)
        
        # Fourth value (index 3): SMA of [12, 14, 16] = 14
        assert mid.iloc[3] == pytest.approx(14.0)
        
        # Fifth value (index 4): SMA of [14, 16, 18] = 16
        assert mid.iloc[4] == pytest.approx(16.0)

    def test_no_lookahead(self):
        series_short = pd.Series([10.0, 12.0, 14.0])
        series_long = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])
        
        mid1, up1, low1 = bollinger_bands(series_short, period=3)
        mid2, up2, low2 = bollinger_bands(series_long, period=3)
        
        assert mid1.iloc[2] == pytest.approx(mid2.iloc[2])
        assert up1.iloc[2] == pytest.approx(up2.iloc[2])
        assert low1.iloc[2] == pytest.approx(low2.iloc[2])

    def test_output_lengths_equal_input(self):
        series = pd.Series(range(100))
        mid, upper, lower = bollinger_bands(series, period=20)
        assert len(mid) == 100
        assert len(upper) == 100
        assert len(lower) == 100
