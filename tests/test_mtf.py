import sqlite3
import pandas as pd
from signal_engine.mtf import compute_mtf_trend, compute_all_mtf_states
from data_layer.db import init_schema

def test_compute_mtf_trend():
    # Insufficient data
    df = pd.DataFrame({"close": [10, 11]})
    assert compute_mtf_trend(df, 50) == False

    # Uptrend: close > EMA
    # EMA2 will be ~15 for the last bar, close is 20
    df = pd.DataFrame({"close": [10, 10, 10, 15, 20]})
    assert compute_mtf_trend(df, 2) == True

    # Downtrend: close <= EMA
    df = pd.DataFrame({"close": [20, 20, 20, 15, 10]})
    assert compute_mtf_trend(df, 2) == False

def test_compute_all_mtf_states():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    # Insert fake candles for 1h (parent of 5m)
    for i in range(50):
        conn.execute(
            "INSERT INTO candles (symbol, timeframe, open_time, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("BTC", "1h", i*1000, 10, 11, 9, 10 + i, 100) # strict uptrend
        )
    conn.commit()

    mtf_parent = {"5m": "1h", "4h": None, "1m": "1d"} # 1d has no data
    symbols = ["BTC"]

    states = compute_all_mtf_states(conn, symbols, mtf_parent, 10, 100)
    
    assert states[("BTC", "5m")] == True
    assert states[("BTC", "1m")] == False # missing parent data
    assert ("BTC", "4h") not in states # no parent

