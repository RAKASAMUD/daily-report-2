"""Tests for Bollinger mean-reversion strategy — Develop 2 Task B1."""

import pandas as pd
import numpy as np
import pytest
import time
from signal_engine.strategies.bollinger_mr import bollinger_mean_reversion

# Default params for testing
PARAMS = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "bb_period": 20,
    "bb_std": 2.0,
    "ema_trend": 200,
    "slope_lookback": 5,
    "use_downtrend_filter": True,
    "atr_period": 14,
    "sl_buffer_atr": 0.2,
    "min_rr": 0.01,  # Lowered for testing so arbitrary bounces pass the RR gate
    "depth_med": 0.5,
    "depth_high": 1.5,
}

def _make_df(closes, lows=None, highs=None, add_ema_warmup=True):
    """
    Helper to generate DataFrame.
    To avoid NaN in EMA200, we can prefix with 200 bars of a flat price.
    """
    base_price = closes[0]
    
    if add_ema_warmup:
        prefix_len = 200
        prefix_closes = [base_price] * prefix_len
        closes = prefix_closes + closes
        
        if lows is None:
            lows = closes
        else:
            lows = [base_price] * prefix_len + lows
            
        if highs is None:
            highs = closes
        else:
            highs = [base_price] * prefix_len + highs
    else:
        if lows is None: lows = closes
        if highs is None: highs = closes

    n = len(closes)
    open_times = [1000000 + i * 3600000 for i in range(n)]
    
    return pd.DataFrame({
        "open_time": open_times,
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [1.0] * n
    })


class TestBollingerMR:
    def test_bounce_confirmed(self):
        # We need bb_period (20) bars to get Bollinger bands. 
        # Flat at 100 for 200 bars (EMA warmup + BB warmup)
        # Then price dips below lower band, then closes above it.
        # Lower band is approx 100 if flat.
        
        # Let's create a specific scenario where we know the band values.
        # We will turn off use_downtrend_filter for simplicity in this test.
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        
        closes = [100.0] * 20 + [100.0, 95.0, 98.0, 102.0]
        # At 95, it should be below lower band (mean~99, std~some value, lower band ~ 98)
        # At 102, it should cross back above lower band.
        
        df = _make_df(closes, add_ema_warmup=False)
        # To make ATR work (needs 14 bars), the 20 flat bars handle it. ATR ~ 0.
        
        # Let's verify with actual values:
        # We want at iloc[-2] (value 98), close < lower
        # At iloc[-1] (value 102), close >= lower
        
        # Let's carefully craft a series.
        closes = [100.0] * 25
        lows   = [100.0] * 25
        highs  = [100.0] * 25
        
        # iloc[-3]: dip starts
        closes[-3] = 90.0; lows[-3] = 88.0; highs[-3] = 100.0
        # iloc[-2]: still below band
        closes[-2] = 92.0; lows[-2] = 91.0; highs[-2] = 95.0
        # iloc[-1]: bounce above lower band, but stay below middle band (~99)
        closes[-1] = 96.0; lows[-1] = 93.0; highs[-1] = 98.0
    
        df = _make_df(closes, lows, highs, add_ema_warmup=True)
        sig = bollinger_mean_reversion(df, params)
        
        assert sig is not None
        assert sig.direction == "long"
        assert sig.strategy == "bollinger_mr"
        assert sig.entry == 96.0
        # tp should be middle band (SMA20). Since mostly 100 with a few 90s, SMA20 ~ 98-99
        assert sig.tp > 95.0 
        # sl should be dip_low - buffer*ATR. lowest low during dip is 88.0
        assert sig.sl < 88.0
        assert sig.rr >= params["min_rr"]
        assert "Bounce off lower BB" in sig.reason

    def test_no_dip_returns_none(self):
        params = PARAMS.copy()
        closes = [100.0] * 25
        df = _make_df(closes)
        sig = bollinger_mean_reversion(df, params)
        assert sig is None

    def test_still_below_returns_none(self):
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        closes = [100.0] * 25
        # iloc[-2] and iloc[-1] both below band
        closes[-2] = 90.0
        closes[-1] = 91.0
        df = _make_df(closes)
        sig = bollinger_mean_reversion(df, params)
        assert sig is None

    def test_already_above_returns_none(self):
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        closes = [100.0] * 25
        # iloc[-3] was below, but iloc[-2] and iloc[-1] are above
        closes[-3] = 80.0
        closes[-2] = 100.0
        closes[-1] = 101.0
        df = _make_df(closes)
        sig = bollinger_mean_reversion(df, params)
        assert sig is None

    def test_downtrend_filter_active(self):
        # close < EMA200 AND EMA200 falling -> None
        params = PARAMS.copy()
        # EMA200 is falling if we create a long downtrend
        closes = [100.0 - i*0.1 for i in range(250)]
        # induce a bounce at the end
        closes[-3] = closes[-4] - 10.0 # big dip below band
        closes[-2] = closes[-4] - 9.0  # still below
        closes[-1] = closes[-4] + 2.0  # bounce above lower band
        
        df = _make_df(closes, add_ema_warmup=False) # already 250 bars
        
        sig = bollinger_mean_reversion(df, params)
        assert sig is None # Filtered out by downtrend

    def test_downtrend_filter_ranging(self):
        # close < EMA200 but EMA200 is flat -> Signal
        params = PARAMS.copy()
        
        # create an uptrend so EMA200 is rising despite the small dip
        closes = [10.0 + i*0.5 for i in range(250)] # Rising EMA200
        # induce a dip
        last_val = closes[-4]
        closes[-3] = last_val - 15.0
        closes[-2] = last_val - 14.0
        closes[-1] = last_val - 7.0
    
        lows = closes.copy()
        lows[-3] = last_val - 20.0
        
        df = _make_df(closes, lows=lows, add_ema_warmup=False)
        
        sig = bollinger_mean_reversion(df, params)
        assert sig is not None
        assert "EMA200 flat" in sig.reason or "EMA200 rising" in sig.reason or "close>EMA200" in sig.reason

    def test_downtrend_filter_off(self):
        # active downtrend but filter OFF -> Signal
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        
        closes = [100.0 - i*0.1 for i in range(250)]
        closes[-3] = closes[-4] - 15.0 # big dip below band
        closes[-2] = closes[-4] - 14.0  # still below
        closes[-1] = closes[-4] - 5.0  # bounce above lower band but below middle
    
        lows = closes.copy()
        lows[-3] -= 5.0
        
        df = _make_df(closes, lows=lows, add_ema_warmup=False)
        
        sig = bollinger_mean_reversion(df, params)
        assert sig is not None

    def test_rr_below_min_rr(self):
        # Bounce, but TP is very close to entry, or SL is very far, making RR < 1.0
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        params["min_rr"] = 5.0 # Unreasonably high requirement
        
        closes = [100.0] * 25
        closes[-3] = 90.0
        closes[-2] = 92.0
        closes[-1] = 99.9 # Entry very close to middle band (~100) -> small TP distance
        
        lows = closes.copy()
        lows[-3] = 50.0 # Very far SL -> large SL distance -> low RR
        
        df = _make_df(closes, lows=lows, add_ema_warmup=True)
        sig = bollinger_mean_reversion(df, params)
        assert sig is None

    def test_multi_bar_dip_finds_lowest_low(self):
        params = PARAMS.copy()
        params["use_downtrend_filter"] = False
        
        closes = [100.0] * 25
        # dip for 3 bars
        closes[-4] = 94.0 # lowest close
        closes[-3] = 95.0
        closes[-2] = 95.0
        closes[-1] = 98.0 # Bounce above lower band (~96.5), below middle (~99)
    
        lows = closes.copy()
        # Make the lowest low at bar -4 (dip start), not the lowest close bar
        lows[-4] = 80.0
        
        df = _make_df(closes, lows=lows, add_ema_warmup=True)
        sig = bollinger_mean_reversion(df, params)
        
        assert sig is not None
        # SL should be based on 80.0
        assert sig.sl < 80.0
        # If it took the wrong bar, SL would be around 94
        assert sig.sl < 85.0

    def test_too_few_rows(self):
        params = PARAMS.copy()
        df = _make_df([100.0, 101.0], add_ema_warmup=False)
        sig = bollinger_mean_reversion(df, params)
        assert sig is None
