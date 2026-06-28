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
