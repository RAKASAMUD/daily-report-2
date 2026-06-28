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
