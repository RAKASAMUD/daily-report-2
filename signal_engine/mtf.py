import pandas as pd
from signal_engine.indicators import ema

def compute_mtf_trend(df_parent: pd.DataFrame, ema_period: int) -> bool:
    """
    Returns True if close[-1] > ema(close, ema_period)[-1] on the parent TF.
    Returns False if insufficient data or close <= ema.
    """
    if df_parent.empty or len(df_parent) < ema_period:
        return False
        
    close = df_parent["close"]
    ema_vals = ema(close, ema_period)
    
    curr_close = close.iloc[-1]
    curr_ema = ema_vals.iloc[-1]
    
    return bool(curr_close > curr_ema)

def compute_all_mtf_states(conn, symbols: list[str], mtf_parent: dict, ema_period: int, candle_limit: int) -> dict:
    """
    Pre-compute MTF states for every (symbol, child_tf) that has a parent.
    Returns {(symbol, child_tf): bool}
    """
    from data_layer.db import get_candles
    
    states = {}
    
    for symbol in symbols:
        for child_tf, parent_tf in mtf_parent.items():
            if parent_tf is None:
                continue
                
            try:
                df_parent = get_candles(conn, symbol, parent_tf, limit=candle_limit)
                is_aligned = compute_mtf_trend(df_parent, ema_period)
                states[(symbol, child_tf)] = is_aligned
            except Exception:
                states[(symbol, child_tf)] = False
                
    return states
