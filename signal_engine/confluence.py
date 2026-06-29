import json
import pandas as pd
from typing import Optional
from datetime import datetime
from signal_engine.checks import ALL_CHECKS, CheckResult
from signal_engine.indicators import atr
from signal_engine.types import Signal

def evaluate_confluence(df: pd.DataFrame, params: dict, mtf_aligned: bool | None = None) -> Optional[Signal]:
    results = [check(df, params) for check in ALL_CHECKS]
    triggered = [c for c in results if c.triggered]
    
    if len(triggered) == 0:
        return None
        
    if params.get("use_mtf_filter", False) and mtf_aligned is not None:
        if not mtf_aligned:
            return None
        
    entry = float(df["close"].iloc[-1])
    
    atr_period = params.get("atr_period", 14)
    atrv = float(atr(df, atr_period).iloc[-1])
    
    tf = params.get("timeframe", "UNKNOWN")
    atr_mult = params.get("atr_mult_by_tf", {}).get(tf, 1.5)
    rr = params.get("rr", 2.0)
    
    sl = entry - (atr_mult * atrv)
    tp = entry + rr * (entry - sl)
    
    checklist = json.dumps([
        {"name": c.name, "triggered": bool(c.triggered), "detail": c.detail} 
        for c in results
    ])
    
    strength = f"{len(triggered)}/{len(ALL_CHECKS)}"
    reason = ", ".join([c.name for c in triggered])
    
    symbol = params.get("symbol", "UNKNOWN")
    timeframe = params.get("timeframe", "UNKNOWN")
    
    if "open_time" in df.columns:
        bar_open_time = int(df["open_time"].iloc[-1])
    else:
        bar_open_time = int(datetime.utcnow().timestamp() * 1000)
        
    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        strategy="confluence",
        bar_open_time=bar_open_time,
        direction="long",
        entry=entry,
        tp=tp,
        sl=sl,
        rr=rr,
        reason=reason,
        strength=strength,
        created_at=int(datetime.utcnow().timestamp() * 1000),
        checklist=checklist
    )
