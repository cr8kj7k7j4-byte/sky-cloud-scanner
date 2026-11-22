"""BRK20 long candidate exactly as pre-registered in PREREGISTRATION_V1.md."""

import config
from engine import Bar, Signal


def _ma(bars: list[Bar], end: int, n: int) -> float | None:
    if end - n + 1 < 0:
        return None
    return sum(b.close for b in bars[end - n + 1:end + 1]) / n


def _avg_volume(bars: list[Bar], end: int, n: int) -> float | None:
    if end - n + 1 < 0:
        return None
    return sum(b.volume for b in bars[end - n + 1:end + 1]) / n


def brk20_signals(symbol: str, bars: list[Bar]) -> list[Signal]:
    """Signals decided on the close of each bar t. Entry rule is applied by the engine."""
    out = []
    for t in range(60, len(bars) - 1):           # need 60 bars for MA60 and 20 for breakout
        window = bars[t - 20:t]                  # prior 20 bars, excludes t
        trigger = max(b.high for b in window)
        bar_t = bars[t]
        ma60 = _ma(bars, t, 60)
        avg_vol = _avg_volume(bars, t, 20)
        if ma60 is None or avg_vol is None:
            continue
        if bar_t.close > config.MAX_PRICE:
            continue
        if avg_vol < config.MIN_AVG_VOLUME_20D:
            continue
        if not (bar_t.close > trigger and bar_t.close > ma60):
            continue
        out.append(Signal(
            symbol=symbol,
            side="long",
            signal_index=t,
            stop=bar_t.low,
            target=None,                          # set after entry is known (2R)
            max_accept=trigger * 1.005,
        ))
    return out
