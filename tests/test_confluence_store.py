import sqlite3
import pytest
from signal_engine.store import init_signals_schema, write_signal, get_signals, migrate_signals_schema
from signal_engine.types import Signal

def test_store_checklist():
    conn = sqlite3.connect(":memory:")
    init_signals_schema(conn)
    migrate_signals_schema(conn)
    
    sig = Signal(
        symbol="BTC", timeframe="1h", strategy="confluence",
        bar_open_time=123, direction="long", entry=10.0,
        tp=12.0, sl=9.0, rr=2.0, reason="EMA Cross",
        strength="1/8", created_at=456, checklist='[{"name": "EMA Cross", "triggered": true, "detail": ""}]'
    )
    
    write_signal(conn, sig)
    
    sigs = get_signals(conn)
    assert len(sigs) == 1
    assert sigs[0].checklist == sig.checklist

def test_legacy_read():
    conn = sqlite3.connect(":memory:")
    init_signals_schema(conn)
    
    # insert without checklist
    conn.execute("""
        INSERT INTO signals 
        (symbol, timeframe, strategy, bar_open_time, direction, entry, tp, sl, rr, reason, strength, created_at)
        VALUES ('ETH', '1h', 'ema', 123, 'long', 1, 2, 0.5, 2.0, 'bla', 'high', 456)
    """)
    conn.commit()
    
    migrate_signals_schema(conn)
    
    sigs = get_signals(conn)
    assert len(sigs) == 1
    assert sigs[0].checklist == ''
