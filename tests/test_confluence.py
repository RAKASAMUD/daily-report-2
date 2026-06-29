import pandas as pd
import numpy as np
import json
from signal_engine.confluence import evaluate_confluence

def test_evaluate_confluence_no_triggers():
    df = pd.DataFrame({
        "open": [10]*300,
        "high": [11]*300,
        "low": [9]*300,
        "close": [10]*300,
        "volume": [1000]*300,
        "open_time": range(0, 300000, 1000)
    })
    
    params = {"symbol": "BTC/USDT", "timeframe": "1h", "atr_period": 14}
    sig = evaluate_confluence(df, params)
    assert sig is None

def test_evaluate_confluence_with_trigger():
    df = pd.DataFrame({
        "open": [10]*299 + [20],
        "high": [11]*299 + [21],
        "low": [9]*299 + [19],
        "close": [10]*299 + [20],
        "volume": [1000]*299 + [5000],
        "open_time": range(0, 300000, 1000)
    })
    
    params = {"symbol": "BTC/USDT", "timeframe": "1h", "atr_period": 14, "fast": 2, "slow": 5}
    sig = evaluate_confluence(df, params)
    
    assert sig is not None
    assert sig.strategy == "confluence"
    assert sig.symbol == "BTC/USDT"
    
    checklist = json.loads(sig.checklist)
    assert len(checklist) == 8
    
    triggered_count = sum(1 for c in checklist if c["triggered"])
    assert triggered_count > 0
    assert sig.strength == f"{triggered_count}/8"
    assert "EMA Cross" in sig.reason

def test_evaluate_confluence_mtf_gate():
    df = pd.DataFrame({
        "open": [10]*299 + [20],
        "high": [11]*299 + [21],
        "low": [9]*299 + [19],
        "close": [10]*299 + [20],
        "volume": [1000]*299 + [5000],
        "open_time": range(0, 300000, 1000)
    })
    params = {"symbol": "BTC/USDT", "timeframe": "5m", "fast": 2, "slow": 5, "use_mtf_filter": True}
    
    # Gate applies and passes
    sig = evaluate_confluence(df, params, mtf_aligned=True)
    assert sig is not None
    
    # Gate applies and blocks
    sig = evaluate_confluence(df, params, mtf_aligned=False)
    assert sig is None
    
    # Gate disabled
    params["use_mtf_filter"] = False
    sig = evaluate_confluence(df, params, mtf_aligned=False)
    assert sig is not None

def test_evaluate_confluence_per_tf_atr():
    df = pd.DataFrame({
        "open": [10]*299 + [20],
        "high": [11]*299 + [21],
        "low": [9]*299 + [19],
        "close": [10]*299 + [20],
        "volume": [1000]*299 + [5000],
        "open_time": range(0, 300000, 1000)
    })
    
    params = {
        "symbol": "BTC/USDT", "fast": 2, "slow": 5, 
        "atr_mult_by_tf": {"5m": 2.5, "1h": 1.5}
    }
    
    params["timeframe"] = "5m"
    sig_5m = evaluate_confluence(df, params)
    
    params["timeframe"] = "1h"
    sig_1h = evaluate_confluence(df, params)
    
    # SL distance should be larger for 5m than 1h (given same entry and ATR)
    assert (sig_5m.entry - sig_5m.sl) > (sig_1h.entry - sig_1h.sl)
