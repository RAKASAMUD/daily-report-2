"""Strategy config — Task A2."""

EMA_CROSS_PARAMS: dict = {
    "fast": 20,
    "slow": 50,
    "trend": 200,
    "use_trend_filter": True,
    "atr_period": 14,
    "atr_mult": 1.5,
    "rr": 2.0,
    "gap_med": 1.0,
    "gap_high": 2.0,
    "trend_med": 2.0,
    "trend_high": 4.0,
}

CANDLE_LIMIT: int = 300  # EMA200 warmup + buffer

MEAN_REV_PARAMS: dict = {
    "bb_period": 20,
    "bb_std": 2.0,
    "ema_trend": 200,
    "slope_lookback": 5,        # bars to measure EMA200 direction
    "use_downtrend_filter": True,
    "atr_period": 14,
    "sl_buffer_atr": 0.2,      # SL = dip_low - buffer * ATR
    "min_rr": 1.0,
    # strength thresholds
    "depth_med": 0.5,           # % below lower band for med strength
    "depth_high": 1.5,          # % below lower band for high strength
}
