"""Fail-closed evidence gates for three Sky research candidates.

Input is JSON with an `observations` array. This does not fetch external data,
reconstruct archived rules, backtest or authorize trading.
Run: python -m research.three_candidate_evidence_gate input.json
"""
import argparse
import datetime as dt
import json
from pathlib import Path

CANDIDATES = {"REVENUE_MOM_5D", "MCR", "ETF_0050_TREND"}
FIELDS = {
    "REVENUE_MOM_5D": ("symbol", "period", "published_at", "observed_at",
                       "decision_at", "source_url", "source_id"),
    "MCR": ("symbol", "decision_at", "observed_at", "source_url",
            "margin_maintenance_ratio_pct", "ratio_asof", "ratio_scope"),
    "ETF_0050_TREND": ("symbol", "decision_at", "observed_at", "source_url",
                       "strategy_total_return_pct", "benchmark_total_return_pct",
                       "cost_pct", "adjustment_basis", "evaluation_start",
                       "evaluation_end"),
}
ISO = "%Y-%m-%dT%H:%M:%S%z"


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


def inspect_row(candidate, row):
    missing = [key for key in FIELDS[candidate]
               if key not in row or row[key] is None or row[key] == ""]
    if missing:
        return ["MISSING_" + k.upper() for k in missing]
    reasons = []
    try:
        decision = timestamp(row["decision_at"])
        observed = timestamp(row["observed_at"])
        if observed > decision:
            reasons.append("LOOKAHEAD_OBSERVED_AFTER_DECISION")
        if candidate == "REVENUE_MOM_5D":
            published = timestamp(row["published_at"])
            if published > observed or published > decision:
                reasons.append("LOOKAHEAD_PUBLICATION")
            if row.get("timestamp_kind") != "ACTUAL_OFFICIAL_FILING":
                reasons.append("UNVERIFIED_PUBLICATION_TIMESTAMP")
        if candidate == "MCR":
            asof = timestamp(row["ratio_asof"])
            if asof > observed or asof > decision:
                reasons.append("LOOKAHEAD_RATIO")
            if row["ratio_scope"] != "VERIFIED_SYMBOL_LEVEL":
                reasons.append("RATIO_SCOPE_NOT_SYMBOL_VERIFIED")
            ratio = float(row["margin_maintenance_ratio_pct"])
            if ratio <= 0:
                reasons.append("INVALID_MAINTENANCE_RATIO")
            if row.get("signal_claim") == "BELOW_130" and ratio >= 130:
                reasons.append("BELOW_130_CLAIM_FALSE")
        if candidate == "ETF_0050_TREND":
            if str(row["symbol"]) != "0050":
                reasons.append("WRONG_ETF_SYMBOL")
            if row["adjustment_basis"] != "TOTAL_RETURN_SAME_BASIS":
                reasons.append("DIVIDEND_SPLIT_BASIS_UNVERIFIED")
            if row["evaluation_start"] >= row["evaluation_end"]:
                reasons.append("INVALID_EVALUATION_WINDOW")
            cost = float(row["cost_pct"])
            if cost < 0:
                reasons.append("NEGATIVE_COST")
            if row.get("benchmark_cost_basis") != row.get("strategy_cost_basis"):
                reasons.append("MISMATCHED_COST_BASIS")
    except (ValueError, TypeError, OverflowError):
        reasons.append("INVALID_TIMESTAMP_OR_NUMERIC")
    return reasons


def evaluate(payload):
    candidate = payload.get("candidate")
    if candidate not in CANDIDATES:
        raise ValueError("candidate must be one of " + ", ".join(sorted(CANDIDATES)))
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError("observations must be a list")
    results = []
    for index, row in enumerate(rows):
        reasons = inspect_row(candidate, row) if isinstance(row, dict) else ["INVALID_ROW"]
        results.append({"index": index, "evidence_valid": not reasons, "reasons": reasons})
    valid = sum(item["evidence_valid"] for item in results)
    return {
        "candidate": candidate,
        "evidence_status": "EVIDENCE_INPUT_PASS" if rows and valid == len(rows)
                           else "INSUFFICIENT_DATA",
        "trading_qualification": "RESEARCH_ONLY_NOT_PRODUCTION",
        "observations": len(rows),
        "valid_observations": valid,
        "invalid_observations": len(rows) - valid,
        "promotion": "BLOCKED_PENDING_FULL_VALIDATION",
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    data = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data + "\n", encoding="utf-8")
    print(data)
    return 0 if result["evidence_status"] == "EVIDENCE_INPUT_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
