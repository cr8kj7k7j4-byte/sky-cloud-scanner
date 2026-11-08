"""Leakage-safe markout of research observations using provided real historical bars.

Caller must provide timestamped OHLCV obtained from an authorized provider.
No synthetic prices, model win probabilities, or order instructions.
"""
from datetime import timedelta
from research.three_model_research_signals import verify_bars, evaluate


def research_markout(symbol, model, bars, horizon=1, roundtrip_cost=0.0045):
    if model not in ("bidirectional_intraday", "next_day", "swing_3_20d"):
        raise ValueError("unknown_model")
    if not 1 <= horizon <= 20 or not 0 <= roundtrip_cost <= 0.05:
        raise ValueError("invalid_research_parameters")
    if not isinstance(bars, list) or len(bars) < 32 + horizon:
        return {"status": "INSUFFICIENT_DATA", "observations": []}
    from research.three_model_research_signals import parse_timestamp
    verified = verify_bars(bars, parse_timestamp(bars[-1]["timestamp"]), 32 + horizon)
    observations = []
    for i in range(31, len(verified) - horizon):
        current = verified[i]
        prior = verified[:i + 1]
        # Signal at bar i close; next bar OPEN entry avoids same-bar execution.
        decision = evaluate(model, symbol, symbol, prior, "HISTORICAL_PROVIDER_BARS", parse_timestamp(current["timestamp"]))
        direction = decision.get("direction")
        if direction not in ("LONG_WATCH", "SHORT_WATCH"):
            continue
        entry = float(bars[i + 1]["open"])
        exit_price = float(bars[i + horizon]["close"])
        if entry <= 0 or exit_price <= 0:
            continue
        sign = 1 if direction == "LONG_WATCH" else -1
        net = sign * (exit_price / entry - 1) - roundtrip_cost
        observations.append({
            "signal_at": current["timestamp"],
            "entry_at": bars[i + 1]["timestamp"],
            "exit_at": bars[i + horizon]["timestamp"],
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "net_return": round(net, 8),
            "research_only": True,
        })
    count = len(observations)
    return {
        "schema": "SKY_RESEARCH_HISTORICAL_MARKOUT_V1",
        "status": "RESEARCH_ONLY" if count else "NO_OBSERVATIONS",
        "symbol": symbol,
        "model": model,
        "observations": observations,
        "observation_count": count,
        "net_average_return": round(sum(x["net_return"] for x in observations) / count, 8) if count else None,
        "positive_net_fraction": round(sum(x["net_return"] > 0 for x in observations) / count, 6) if count else None,
        "cost_assumption": roundtrip_cost,
        "limitations": "No fills, borrow availability, intrabar stop order, slippage or calibrated probability; overlapping samples are not independent.",
        "production_signal": False,
    }
