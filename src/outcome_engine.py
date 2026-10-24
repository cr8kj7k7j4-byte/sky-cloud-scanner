from dataclasses import dataclass, asdict
from datetime import datetime

OUTCOME_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class TradeOutcome:
    schema_version: str
    entry: float | None
    exit: float | None
    gross_pnl: float | None
    net_pnl: float | None
    r_multiple: float | None
    mfe_pct: float | None
    mae_pct: float | None
    holding_bars: int
    hit_stop: bool
    hit_target: bool
    status: str

    def to_dict(self):
        return asdict(self)


def _f(v):
    return None if v is None else float(v)


def evaluate_long_outcome(*, entry, stop, target, bars, exit_price=None, fee_rate=0.0, tax_rate=0.0, slippage_rate=0.0):
    entry = _f(entry)
    stop = _f(stop)
    target = _f(target)
    if entry is None or stop is None or entry <= 0 or stop <= 0 or entry == stop:
        return TradeOutcome(
            OUTCOME_SCHEMA_VERSION, entry, _f(exit_price), None, None, None,
            None, None, 0, False, False, "INVALID_INPUT"
        )

    highs=[]; lows=[]; closes=[]
    for b in bars or []:
        try:
            if b.get("high") is not None: highs.append(float(b["high"]))
            if b.get("low") is not None: lows.append(float(b["low"]))
            if b.get("close") is not None: closes.append(float(b["close"]))
        except Exception:
            continue

    if not highs or not lows:
        return TradeOutcome(
            OUTCOME_SCHEMA_VERSION, entry, _f(exit_price), None, None, None,
            None, None, len(closes), False, False, "INSUFFICIENT_BARS"
        )

    max_high=max(highs); min_low=min(lows)
    mfe_pct=(max_high/entry-1.0)*100.0
    mae_pct=(min_low/entry-1.0)*100.0
    hit_stop=min_low <= stop
    hit_target=(target is not None and max_high >= target)

    if exit_price is None:
        exit_price = closes[-1] if closes else entry
    exit_price=float(exit_price)

    gross=exit_price-entry
    round_trip_cost=entry*fee_rate + exit_price*(fee_rate+tax_rate) + entry*slippage_rate + exit_price*slippage_rate
    net=gross-round_trip_cost
    risk=abs(entry-stop)
    r=net/risk if risk>0 else None

    return TradeOutcome(
        schema_version=OUTCOME_SCHEMA_VERSION,
        entry=round(entry,4),
        exit=round(exit_price,4),
        gross_pnl=round(gross,4),
        net_pnl=round(net,4),
        r_multiple=round(r,4) if r is not None else None,
        mfe_pct=round(mfe_pct,4),
        mae_pct=round(mae_pct,4),
        holding_bars=len(closes),
        hit_stop=bool(hit_stop),
        hit_target=bool(hit_target),
        status="COMPLETE",
    )
