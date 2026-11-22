"""Daily next-open trade simulator.

Causality rules (Gate 0):
- A signal is decided on the CLOSE of bar i.
- Entry happens at the OPEN of bar i+1, and only if that open is within the
  pre-registered max-accept price.
- The entry bar is checked for the STOP only (a stop hit on the entry day is
  real risk with daily bars). The target is NOT taken on the entry bar, because
  a daily bar cannot show whether its high came before or after the entry
  (conservative: fewer wins, never optimistic).
- If stop and target are both touched on the same bar, the stop is taken first
  (conservative, as in the frozen P0-S protocol).
"""

import math
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: str            # "long" or "short"
    signal_index: int    # index of the bar whose close produced the signal
    stop: float
    target: float
    max_accept: float    # worst acceptable entry price


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    exit_reason: str     # "stop", "target", "time", "end_of_data"
    shares: int
    gross_return: float  # signed, before costs
    net_return: float    # after round-trip cost


def size_shares(entry: float, stop: float, cost_rate: float,
                one_r: float = config.ONE_R_TWD,
                max_notional: float = config.MAX_SINGLE_NOTIONAL_SWING_TWD) -> int:
    """Shares limited by the 1R budget (including estimated cost) and the notional cap."""
    per_share_risk = abs(entry - stop) + entry * cost_rate
    if per_share_risk <= 0 or entry <= 0:
        return 0
    by_risk = math.floor(one_r / per_share_risk)
    by_notional = math.floor(max_notional / entry)
    return max(0, min(by_risk, by_notional))


def simulate_trade(bars: list[Bar], sig: Signal, cost_rate: float,
                   max_hold_bars: int = 1) -> Trade | None:
    """Simulate one trade from a signal. Returns None if the entry is not filled."""
    entry_i = sig.signal_index + 1
    if entry_i >= len(bars):
        return None
    entry_bar = bars[entry_i]
    entry = entry_bar.open
    is_long = sig.side == "long"

    # Entry filter: the open must not be worse than the max-accept price.
    if is_long and entry > sig.max_accept:
        return None
    if not is_long and entry < sig.max_accept:
        return None
    # Stop must lie on the loss side of the entry, otherwise the setup is invalid.
    if (is_long and sig.stop >= entry) or (not is_long and sig.stop <= entry):
        return None

    shares = size_shares(entry, sig.stop, cost_rate)
    if shares == 0:
        return None

    exit_price, exit_date, reason = None, None, None
    last_i = min(len(bars) - 1, entry_i + max_hold_bars)
    for j in range(entry_i, last_i + 1):
        b = bars[j]
        if is_long:
            stop_hit = b.low <= sig.stop
            target_hit = b.high >= sig.target
        else:
            stop_hit = b.high >= sig.stop
            target_hit = b.low <= sig.target
        if j == entry_i:
            target_hit = False   # see module docstring

        # Stop first on same-bar ambiguity. Gap-throughs fill at the open.
        if stop_hit:
            exit_price = _gap_fill(b.open, sig.stop, is_long, loss=True)
            reason = "stop"
        elif target_hit:
            exit_price = _gap_fill(b.open, sig.target, is_long, loss=False)
            reason = "target"
        if reason:
            exit_date = b.date
            break

    if reason is None:
        b = bars[last_i]
        exit_price, exit_date = b.close, b.date
        reason = "time" if last_i < len(bars) - 1 or last_i - entry_i >= max_hold_bars else "end_of_data"

    sign = 1 if is_long else -1
    gross = sign * (exit_price - entry) / entry
    net = gross - cost_rate
    return Trade(sig.symbol, sig.side, entry_bar.date, entry, exit_date,
                 exit_price, reason, shares, gross, net)


def _gap_fill(open_price: float, level: float, is_long: bool, loss: bool) -> float:
    """If the bar gaps through the level at the open, fill at the open; otherwise at the level."""
    if is_long:
        # Long stop triggers when price falls to/below stop; target when it rises to/above.
        if loss:
            return min(open_price, level)
        return max(open_price, level)
    if loss:
        return max(open_price, level)
    return min(open_price, level)
