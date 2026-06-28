"""Signal formatting — Task B1 / amended D2."""

from datetime import datetime, timezone
from signal_engine.types import Signal
from tracking.stats import confidence_label


def _format_price(price: float) -> str:
    """Format price with thousands separator and appropriate decimals."""
    # For large numbers like 60305, drop decimals if they are zero
    # For small numbers like 0.05, keep decimals
    # A simple approach: use ,.Xf and remove trailing zeros if it has a decimal point
    s = f"{price:,.4f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def format_signal(sig: Signal, stats: dict | None = None) -> str:
    """
    Format a Signal into a scannable text card for delivery.

    stats: optional dict keyed by (strategy, timeframe) from aggregate_stats().
           If None or group not found, confidence shows "building (n=0)".
    """
    direction_upper = sig.direction.upper()
    icon = "📈" if direction_upper == "LONG" else "📉"
    
    tp_pct = (sig.tp - sig.entry) / sig.entry * 100
    sl_pct = (sig.sl - sig.entry) / sig.entry * 100
    
    tp_pct_str = f"+{tp_pct:.1f}%" if tp_pct > 0 else f"{tp_pct:.1f}%"
    sl_pct_str = f"+{sl_pct:.1f}%" if sl_pct > 0 else f"{sl_pct:.1f}%"
    
    strength_str = sig.strength.upper() if sig.strength else "n/a"
    
    dt = datetime.fromtimestamp(sig.bar_open_time / 1000.0, tz=timezone.utc)
    time_str = dt.strftime("%Y-%m-%d %H:%M UTC")

    # Confidence: look up (strategy, timeframe) in stats snapshot
    group = stats.get((sig.strategy, sig.timeframe)) if stats else None
    conf_str = confidence_label(group)
    
    lines = [
        f"{icon} {direction_upper} \u00b7 {sig.symbol} \u00b7 {sig.timeframe}",
        f"Setup: {sig.reason}",
        f"Entry: {_format_price(sig.entry)}",
        f"TP:    {_format_price(sig.tp)}  ({tp_pct_str})",
        f"SL:    {_format_price(sig.sl)}  ({sl_pct_str})",
        f"R:R:   {sig.rr:.1f}",
        f"Strength: {strength_str}",
        f"Confidence: {conf_str}",
        f"Bar:   {time_str}",
    ]
    return "\n".join(lines)
