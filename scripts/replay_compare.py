import sqlite3, pandas as pd
from data_layer.config import DB_PATH, SYMBOLS, TIMEFRAMES, TIMEFRAME_MS
from data_layer.db import get_candles
from signal_engine.confluence_config import CONFLUENCE_PARAMS, CONFLUENCE_CANDLE_LIMIT
from signal_engine.confluence_config import ATR_MULT_BY_TF, MTF_PARENT, MTF_TREND_EMA, USE_MTF_FILTER
from signal_engine.confluence import evaluate_confluence
from signal_engine.indicators import ema

def run_replay_compare():
    print("Memulai replay comparison (Old vs New MTF)...", flush=True)
    conn = sqlite3.connect(DB_PATH)

    for tf in ['5m', '15m', '1h']:
        old_count = 0; new_count = 0
        for sym in SYMBOLS:
            df = pd.read_sql_query(
                'SELECT open_time, open, high, low, close, volume FROM candles '
                'WHERE symbol=? AND timeframe=? ORDER BY open_time ASC',
                conn, params=(sym, tf))

            parent_tf = MTF_PARENT.get(tf)
            parent_aligned_cache = {}
            if parent_tf:
                pdf = pd.read_sql_query(
                    'SELECT open_time, open, high, low, close, volume FROM candles '
                    'WHERE symbol=? AND timeframe=? ORDER BY open_time ASC',
                    conn, params=(sym, parent_tf))
                if len(pdf) > MTF_TREND_EMA:
                    pema = ema(pdf['close'], MTF_TREND_EMA)
                    for idx in range(len(pdf)):
                        parent_aligned_cache[int(pdf['open_time'].iloc[idx])] = bool(pdf['close'].iloc[idx] > pema.iloc[idx])

            for i in range(CONFLUENCE_CANDLE_LIMIT, len(df)):
                w = df.iloc[i - CONFLUENCE_CANDLE_LIMIT + 1 : i + 1]
                params_old = {**CONFLUENCE_PARAMS, 'symbol': sym, 'timeframe': tf, 'atr_mult': 1.5, 'use_mtf_filter': False}
                params_new = {**CONFLUENCE_PARAMS, 'symbol': sym, 'timeframe': tf, 'atr_mult_by_tf': ATR_MULT_BY_TF, 'use_mtf_filter': True}

                s_old = evaluate_confluence(w, params_old, mtf_aligned=None)
                
                bar_time = int(w['open_time'].iloc[-1])
                parent_tf_ms = TIMEFRAME_MS.get(parent_tf, 0) if parent_tf else 0
                mtf_ok = None
                if parent_tf and parent_tf_ms > 0:
                    parent_bar = (bar_time // parent_tf_ms) * parent_tf_ms
                    mtf_ok = parent_aligned_cache.get(parent_bar, False)
                s_new = evaluate_confluence(w, params_new, mtf_aligned=mtf_ok)

                if s_old: old_count += 1
                if s_new: new_count += 1

        reduction = round((1 - new_count/max(old_count,1))*100, 1)
        print(f'{tf}: old={old_count} new={new_count} reduction={reduction}%', flush=True)

if __name__ == "__main__":
    run_replay_compare()
