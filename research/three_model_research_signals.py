"""Three-horizon research observations. Never an AI prediction or executable order."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

SPECS = {"bidirectional_intraday": ("bars_5m", 26), "next_day": ("bars_daily", 26),
         "swing_3_20d": ("bars_daily", 31)}

def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing_timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("timezone_required")
    return dt

def verify_bars(raw, as_of, minimum):
    if not isinstance(raw, list) or len(raw) < minimum:
        raise ValueError("insufficient_bars")
    records = []
    previous = None
    for bar in raw:
        if not isinstance(bar, dict):
            raise ValueError("invalid_bar")
        timestamp = parse_timestamp(bar.get("timestamp"))
        if timestamp > as_of:
            raise ValueError("future_bar")
        if previous is not None and timestamp <= previous:
            raise ValueError("unordered_or_duplicate_bars")
        previous = timestamp
        try:
            o, h, l, c, v = (float(bar[k]) for k in ("open", "high", "low", "close", "volume"))
        except (KeyError, ValueError, TypeError):
            raise ValueError("invalid_ohlcv") from None
        if not all(map(math.isfinite, (o, h, l, c, v))) or not (0 < l <= min(o, c) <= max(o, c) <= h and v >= 0):
            raise ValueError("invalid_ohlcv")
        records.append({"timestamp": timestamp.isoformat(), "close": c, "range_pct": (h-l)/c*100, "volume": v})
    return records

def evaluate(model, symbol, name, records, source, as_of):
    closes = [r["close"] for r in records]
    price = closes[-1]
    ma5, ma20 = sum(closes[-5:])/5, sum(closes[-20:])/20
    change = price / closes[-6] - 1
    previous_volume = sum(r["volume"] for r in records[-6:-1]) / 5
    vol_ratio = records[-1]["volume"] / previous_volume if previous_volume > 0 else 0
    avg_range = sum(r["range_pct"] for r in records[-20:]) / 20
    direction = "NO_TRADE"
    reasons = []
    if previous_volume <= 0 or avg_range <= 0:
        reasons.append("insufficient_volume_or_range")
    elif vol_ratio >= 1 and price > ma5 > ma20 and change > 0:
        direction = "LONG_WATCH"
    elif vol_ratio >= 1 and price < ma5 < ma20 and change < 0:
        direction = "SHORT_WATCH"
    else:
        reasons.append("unconfirmed_trend")
    # Illustrative, unrounded reference levels only; not executable prices.
    stop = targets = rr = None
    if direction != "NO_TRADE":
        pct = max(1.0, avg_range * 2)
        sign = 1 if direction == "LONG_WATCH" else -1
        stress_rr = (2*pct - 0.65)/(pct + 0.65)
        if stress_rr < 1.5:
            direction = "NO_TRADE"
            reasons.append("cost_stress_rr_below_1_5")
        else:
            stop = round(price*(1-sign*pct/100), 4)
            targets = [round(price*(1+sign*pct*k/100), 4) for k in (2, 3)]
            rr = {"primary_0_45pct": round((2*pct-0.45)/(pct+0.45), 4),
                  "stress_0_65pct": round(stress_rr, 4)}
    identity = [model, symbol, records[-1]["timestamp"], source, direction]
    signal_id = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    return {"signal_id": signal_id, "model_id": model, "symbol": symbol, "stock_name": name,
            "data_source": source, "as_of": as_of.isoformat(), "bar_time": records[-1]["timestamp"],
            "reference_close": price, "direction": direction, "stop_reference": stop,
            "target_references": targets, "reference_rr": rr, "rejection_reasons": reasons,
            "signal_class": "RESEARCH_OBSERVATION_NOT_AI_PREDICTION", "trained_model_used": False,
            "production_signal": False, "order_authorized": False, "eligible_strategy_trade": False,
            "realized_net_pnl": None}

def generate(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")
    as_of = parse_timestamp(payload.get("as_of"))
    if payload.get("source") != "FUGLE":
        raise ValueError("unverified_source_not_fugle")
    symbols = payload.get("symbols")
    if not isinstance(symbols, dict) or not symbols:
        raise ValueError("missing_symbols")
    observations = []
    for symbol, data in sorted(symbols.items()):
        if not isinstance(symbol, str) or not symbol.isdigit() or len(symbol) not in (4, 5) or not isinstance(data, dict):
            raise ValueError("invalid_symbol")
        for model, (field, minimum) in SPECS.items():
            try:
                records = verify_bars(data.get(field), as_of, minimum)
                item = evaluate(model, symbol, data.get("name"), records, payload["source"], as_of)
            except ValueError as exc:
                item = {"signal_id": None, "model_id": model, "symbol": symbol,
                        "stock_name": data.get("name"), "direction": "NO_TRADE",
                        "rejection_reasons": [str(exc)], "trained_model_used": False,
                        "signal_class": "RESEARCH_OBSERVATION_NOT_AI_PREDICTION",
                        "production_signal": False, "order_authorized": False,
                        "eligible_strategy_trade": False, "realized_net_pnl": None}
            observations.append(item)
    return {"schema": "sky-three-research-observations-v1",
            "as_of": as_of.isoformat(), "claimed_source": payload["source"],
            "provider_response_verified": False,
            "model_training_status": "UNTRAINED_OR_UNVERIFIED",
            "production_signal": False, "order_authorized": False, "observations": observations}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", default="research_output/three_models/research_observations.json")
    args = parser.parse_args()
    result = generate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "count": len(result["observations"]),
                      "production_signal": False}, ensure_ascii=False))

if __name__ == "__main__":
    main()
