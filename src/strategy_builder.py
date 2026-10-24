from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class StrategyPlan:
    setup: str
    trigger: float
    max_entry: float
    stop: float
    target: float
    rr: float
    source: str = "5m_breakout_candidate"
    production_eligible: bool = False

    def to_dict(self):
        return asdict(self)


def _bars(candles):
    if not isinstance(candles, dict):
        return []
    rows = candles.get("data", [])
    if not isinstance(rows, list):
        return []
    out = []
    for x in rows:
        try:
            out.append({
                "high": float(x["high"]),
                "low": float(x["low"]),
                "close": float(x["close"]),
                "volume": float(x.get("volume") or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return out


def build_breakout_plan(candidate, candles, lookback=4, target_rr=2.0, max_entry_r=0.25):
    """
    P0-S MVP: deterministic research-only breakout plan.

    Rules:
    - requires at least lookback + 1 valid 5m bars
    - trigger = highest high of the previous lookback bars
    - stop = lowest low of the previous lookback bars
    - target = trigger + target_rr * unit risk
    - max_entry = trigger + max_entry_r * unit risk

    It intentionally does not use future bars and does not claim statistical
    edge. This is a candidate plan for later OOS / cost-aware validation.
    """
    rows = _bars(candles)
    if len(rows) < lookback + 1:
        return None

    hist = rows[-(lookback + 1):-1]
    trigger = max(x["high"] for x in hist)
    stop = min(x["low"] for x in hist)

    if trigger <= 0 or stop <= 0 or stop >= trigger:
        return None

    risk = trigger - stop
    target = trigger + float(target_rr) * risk
    max_entry = trigger + float(max_entry_r) * risk
    rr = (target - trigger) / risk

    # Optional VWAP/average guard: if a valid average price exists and trigger
    # is already below it, do not promote this breakout candidate.
    avg_price = candidate.get("avg_price") if isinstance(candidate, dict) else None
    try:
        if avg_price is not None and trigger < float(avg_price):
            return None
    except (TypeError, ValueError):
        pass

    return StrategyPlan(
        setup="5分K平台突破候選",
        trigger=round(trigger, 4),
        max_entry=round(max_entry, 4),
        stop=round(stop, 4),
        target=round(target, 4),
        rr=round(rr, 3),
    )


def apply_plan(candidate, plan):
    if not plan:
        return candidate
    candidate = dict(candidate)
    p = plan.to_dict()
    candidate["strategy_plan"] = p
    candidate["setup"] = p["setup"]
    candidate["trigger"] = p["trigger"]
    candidate["max_entry"] = p["max_entry"]
    candidate["stop"] = p["stop"]
    candidate["target"] = p["target"]
    return candidate
