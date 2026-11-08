"""Read-only probability evidence gate for intraday and next-day direction.

Existing rule-based LONG_WATCH/SHORT_WATCH decisions are observations, not
calibrated probabilities. No raw score is converted to a probability.
This gate never trains models, places orders or changes Production.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

HORIZONS = ("bidirectional_intraday", "next_day")
MIN_OBSERVATIONS = 200
MIN_DAYS = 20
MIN_REGIMES = 2
MAX_SYMBOL_SHARE = 0.20
MIN_OUTCOME_COMPLETENESS = 0.95

def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp_missing")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.utcoffset() is None:
        raise ValueError("timestamp_timezone_required")
    return dt

def check_horizon(rows, *, training_verified=False, cost_gate="UNKNOWN",
                  independent_oos=False, forward_only=False):
    """Accept only observed historical predictions with resolved future outcomes."""
    errors = []
    seen = set()
    valid = []
    total = 0
    complete = 0
    for row in rows:
        total += 1
        if not isinstance(row, dict):
            errors.append("invalid_record")
            continue
        key = row.get("prediction_id")
        if not isinstance(key, str) or not key or key in seen:
            errors.append("missing_or_duplicate_prediction_id")
            continue
        seen.add(key)
        if row.get("actual_up") is None:
            continue
        complete += 1
        p, outcome = row.get("p_up"), row.get("actual_up")
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            errors.append("probability_invalid")
            continue
        if type(outcome) is not int or outcome not in (0, 1):
            errors.append("outcome_invalid")
            continue
        try:
            before, after = _time(row.get("prediction_at")), _time(row.get("outcome_at"))
            if before >= after:
                raise ValueError("not_future_outcome")
        except (ValueError, TypeError):
            errors.append("timestamp_invalid_or_lookahead")
            continue
        if not isinstance(row.get("symbol"), str) or not row["symbol"]:
            errors.append("symbol_missing")
            continue
        if row.get("regime") not in ("BULL", "NEUTRAL", "BEAR"):
            errors.append("regime_unverified")
            continue
        valid.append((row, float(p), outcome, before))
    n = len(valid)
    days = {x[3].date().isoformat() for x in valid}
    regimes = {x[0]["regime"] for x in valid}
    counts = Counter(x[0]["symbol"] for x in valid)
    concentration = max(counts.values(), default=0) / n if n else None
    coverage = complete / total if total else 0.0
    brier = sum((p-y)**2 for _,p,y,_ in valid)/n if n else None
    prevalence = sum(y for _,_,y,_ in valid)/n if n else None
    baseline_brier = prevalence*(1-prevalence) if n else None
    # Ten-bin expected calibration error, not enough alone for trade eligibility.
    ece = None
    if n:
        weighted_error = 0.0
        for bin_index in range(10):
            group = [(p,y) for _,p,y,_ in valid if min(int(p*10),9)==bin_index]
            if group:
                avg_p = sum(p for p,_ in group)/len(group)
                avg_y = sum(y for _,y in group)/len(group)
                weighted_error += len(group)/n*abs(avg_p-avg_y)
        ece = weighted_error
    gates = {
        "trained_model_proof": training_verified is True,
        "independent_oos": independent_oos is True,
        "genuine_forward_days": forward_only is True,
        "cost_after_trade_gate": cost_gate == "PASS",
        "sample_count": n >= MIN_OBSERVATIONS,
        "trading_days": len(days) >= MIN_DAYS,
        "market_regimes": len(regimes) >= MIN_REGIMES,
        "outcome_completeness": coverage >= MIN_OUTCOME_COMPLETENESS,
        "symbol_concentration": concentration is not None and concentration <= MAX_SYMBOL_SHARE,
        "timestamp_and_probability_integrity": not errors and n == complete,
        "brier_better_than_base_rate": brier is not None and baseline_brier is not None and brier < baseline_brier,
        "calibration_ece": ece is not None and ece <= 0.10,
    }
    eligible = all(gates.values())
    return {
        "status": "CALIBRATION_REVIEW_CANDIDATE" if eligible else "INSUFFICIENT_DATA",
        "display_probability": eligible,
        "production_trade_eligible": False,
        "observed": {"records": total, "valid_resolved": n, "forward_days": len(days),
                     "regimes": sorted(regimes), "outcome_coverage": round(coverage,6),
                     "top_symbol_share": round(concentration,6) if concentration is not None else None,
                     "brier": round(brier,6) if brier is not None else None,
                     "base_rate_brier": round(baseline_brier,6) if baseline_brier is not None else None,
                     "calibration_ece": round(ece,6) if ece is not None else None},
        "gates": gates, "errors": sorted(set(errors)),
        "note": "Review candidate is NOT Production approval. Scores are never probabilities.",
    }

def audit(payload):
    if not isinstance(payload, dict):
        raise ValueError("input_must_be_object")
    models = payload.get("models") or {}
    if not isinstance(models, dict):
        raise ValueError("models_must_be_object")
    results = {}
    for name in HORIZONS:
        entry = models.get(name) or {}
        if not isinstance(entry, dict):
            raise ValueError("model_entry_must_be_object")
        rows = entry.get("predictions") or []
        if not isinstance(rows, list):
            raise ValueError("predictions_must_be_list")
        results[name] = check_horizon(
            rows, training_verified=entry.get("training_verified"),
            cost_gate=entry.get("cost_gate"), independent_oos=entry.get("independent_oos"),
            forward_only=entry.get("forward_only"))
    return {"schema": "SKY_PROBABILITY_EVIDENCE_GATE_V1",
            "probability_definition": "P(next horizon close > reference close); not a profit probability",
            "trained_ai_inference_executed": False,
            "fugle_api_called": False, "production_changed": False,
            "models": results}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("research_output/probability_evidence_gate.json"))
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8")) if args.input and args.input.is_file() else {}
    result = audit(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v["status"] for k,v in result["models"].items()}, ensure_ascii=False))

if __name__ == "__main__":
    main()
