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



def evaluate_shadow_long_path(
    *,
    entry,
    stop,
    target,
    bars,
    fee_rate=None,
    tax_rate=None,
    slippage_rate=None,
    entry_impact_rate=None,
    exit_impact_rate=None,
):
    """Conservative counterfactual long outcome for Shadow research.

    - Uses sequential bars after the observation/trigger time.
    - If stop and target are both touched in the same bar, stop wins.
    - Missing explicit cost assumptions never silently become zero.
    - This is research evidence, not an actual fill record.
    """
    entry = _f(entry)
    stop = _f(stop)
    target = _f(target)
    if (
        entry is None or stop is None or target is None
        or entry <= 0 or stop <= 0 or target <= 0
        or stop >= entry or target <= entry
    ):
        return {
            "status": "INVALID_INPUT",
            "outcome_type": "COUNTERFACTUAL_SHADOW",
            "entry": entry,
            "stop": stop,
            "target": target,
        }

    clean = []
    for b in bars or []:
        try:
            high = float(b["high"])
            low = float(b["low"])
            close = float(b["close"])
        except Exception:
            continue
        clean.append({"high": high, "low": low, "close": close})

    if not clean:
        return {
            "status": "INSUFFICIENT_BARS",
            "outcome_type": "COUNTERFACTUAL_SHADOW",
            "entry": entry,
            "stop": stop,
            "target": target,
        }

    max_high = entry
    min_low = entry
    exit_price = clean[-1]["close"]
    exit_reason = "HORIZON_CLOSE"
    exit_bar_index = len(clean) - 1
    ambiguous_same_bar = False

    for i, b in enumerate(clean):
        max_high = max(max_high, b["high"])
        min_low = min(min_low, b["low"])
        hit_stop = b["low"] <= stop
        hit_target = b["high"] >= target

        if hit_stop and hit_target:
            exit_price = stop
            exit_reason = "STOP"
            exit_bar_index = i
            ambiguous_same_bar = True
            break
        if hit_stop:
            exit_price = stop
            exit_reason = "STOP"
            exit_bar_index = i
            break
        if hit_target:
            exit_price = target
            exit_reason = "TARGET"
            exit_bar_index = i
            break

    used = clean[: exit_bar_index + 1]
    if used:
        max_high = max([entry] + [x["high"] for x in used])
        min_low = min([entry] + [x["low"] for x in used])

    risk = entry - stop
    gross_pnl_per_share = exit_price - entry
    gross_r = gross_pnl_per_share / risk if risk > 0 else None
    mfe_r = (max_high - entry) / risk if risk > 0 else None
    mae_r = (entry - min_low) / risk if risk > 0 else None

    if entry_impact_rate is None and slippage_rate is not None:
        entry_impact_rate = slippage_rate
    if exit_impact_rate is None and slippage_rate is not None:
        exit_impact_rate = slippage_rate

    costs_complete = all(
        x is not None
        for x in (fee_rate, tax_rate, entry_impact_rate, exit_impact_rate)
    )
    net_pnl_per_share = None
    net_r = None
    total_cost_per_share = None
    if costs_complete:
        fee_rate = float(fee_rate)
        tax_rate = float(tax_rate)
        entry_impact_rate = float(entry_impact_rate)
        exit_impact_rate = float(exit_impact_rate)
        total_cost_per_share = (
            entry * fee_rate
            + exit_price * (fee_rate + tax_rate)
            + entry * entry_impact_rate
            + exit_price * exit_impact_rate
        )
        net_pnl_per_share = gross_pnl_per_share - total_cost_per_share
        net_r = net_pnl_per_share / risk if risk > 0 else None

    return {
        "status": "COMPLETE" if costs_complete else "COST_INPUT_REQUIRED",
        "outcome_type": "COUNTERFACTUAL_SHADOW",
        "fill_assumption": "TRIGGER_PRICE_COUNTERFACTUAL",
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "exit": round(exit_price, 4),
        "exit_reason": exit_reason,
        "holding_bars": exit_bar_index + 1,
        "ambiguous_same_bar": ambiguous_same_bar,
        "gross_pnl_per_share": round(gross_pnl_per_share, 6),
        "gross_r_multiple": round(gross_r, 6) if gross_r is not None else None,
        "net_pnl_per_share": (
            round(net_pnl_per_share, 6)
            if net_pnl_per_share is not None else None
        ),
        "r_multiple": round(net_r, 6) if net_r is not None else None,
        "mfe_r": round(mfe_r, 6) if mfe_r is not None else None,
        "mae_r": round(mae_r, 6) if mae_r is not None else None,
        "max_price": round(max_high, 4),
        "min_price": round(min_low, 4),
        "total_cost_per_share": (
            round(total_cost_per_share, 6)
            if total_cost_per_share is not None else None
        ),
        "cost_assumptions": {
            "fee_rate_per_side": fee_rate,
            "sell_tax_rate": tax_rate,
            "entry_impact_rate": entry_impact_rate,
            "exit_impact_rate": exit_impact_rate,
        },
        "research_only": True,
    }
