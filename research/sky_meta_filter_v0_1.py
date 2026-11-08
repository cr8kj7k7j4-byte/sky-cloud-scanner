"""Sky Meta-Filter V0.1: fail-closed offline research evidence evaluator.

Evaluates *frozen* AI scores attached to actual eligible Sky v1.4 candidate
observations. Does not generate candidates, scores, orders or executable signals.
No source of training labels, no strategy promotion, no automatic model fitting.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
import math
from pathlib import Path


SCHEMA = "sky-meta-filter-observation-v0.1"
ALLOWED_DECISIONS = frozenset({"ACCEPT", "REJECT"})
RESEARCH_STATUS = "HOLD_INSUFFICIENT_DATA"


def stamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid_timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_timestamp") from exc
    if dt.utcoffset() is None:
        raise ValueError("timestamp_timezone_required")
    return dt


def finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid_" + name)
    if not math.isfinite(value):
        raise ValueError("nonfinite_" + name)
    return float(value)


def validate_observation(item):
    """One immutable research observation, with a counterfactual LONG-only exit.

    Missing outcomes are preserved in the denominator. No inferred fills, no
    realized PnL. Fees/stress costs computed per share on entry/stop risk.
    """
    if not isinstance(item, dict) or item.get("schema") != SCHEMA:
        raise ValueError("unknown_observation_schema")
    if item.get("production_signal") is not False or item.get("order_authorized") is not False:
        raise ValueError("production_or_order_claim_forbidden")
    if item.get("baseline_model") != "Sky Day Trading v1.4 Dynamic Capital Rotation":
        raise ValueError("baseline_strategy_mismatch")
    if item.get("baseline_eligible") is not True:
        raise ValueError("original_candidate_not_eligible")
    if item.get("side") != "LONG":
        raise ValueError("long_only_pilot")
    for key in ("signal_id", "symbol", "model_version", "source_event_id"):
        if not isinstance(item.get(key), str) or not item[key]:
            raise ValueError("missing_" + key)
    if not item["symbol"].isdigit() or len(item["symbol"]) not in (4, 5):
        raise ValueError("bad_symbol")
    if item.get("model_decision") not in ALLOWED_DECISIONS:
        raise ValueError("invalid_model_decision")
    score = finite(item.get("model_score"), "score")
    if not 0 <= score <= 1:
        raise ValueError("score_outside_unit_interval")
    event = stamp(item.get("candidate_at"))
    scored = stamp(item.get("scored_at"))
    if scored < event:
        raise ValueError("score_before_candidate")
    entry = stamp(item.get("entry_at"))
    if not scored < entry:
        raise ValueError("post_entry_score_leakage")
    if event.date() != entry.date():
        raise ValueError("not_same_day_intraday")
    price = finite(item.get("entry_proxy"), "entry_proxy")
    stop = finite(item.get("stop_proxy"), "stop_proxy")
    if price <= 0 or stop <= 0 or price <= stop:
        raise ValueError("invalid_long_stop_risk")
    # No N or decision threshold is selected from outcomes.
    result = {"signal_id": item["signal_id"], "symbol": item["symbol"],
              "decision_date": event.date().isoformat(),
              "model_version": item["model_version"], "score": score,
              "model_decision": item["model_decision"],
              "regime": item.get("regime", "UNVERIFIED"),
              "outcome_status": "PENDING", "primary_net_r": None,
              "stress_net_r": None}
    if item.get("exit_proxy") is None or item.get("exit_at") is None:
        if item.get("exit_proxy") is not None or item.get("exit_at") is not None:
            raise ValueError("partial_outcome")
        return result
    exit_at = stamp(item["exit_at"])
    if exit_at <= entry or exit_at.date() != event.date():
        raise ValueError("invalid_intraday_exit_at")
    exit_price = finite(item["exit_proxy"], "exit_proxy")
    if exit_price <= 0:
        raise ValueError("invalid_exit_proxy")
    if item.get("counterfactual_evidence_verified") is not True:
        raise ValueError("unverified_counterfactual_outcome")
    risk = price - stop
    result["outcome_status"] = "COUNTERFACTUAL_ONLY"
    result["gross_r"] = (exit_price - price)/risk
    result["primary_net_r"] = (exit_price - price - price * .0045)/risk
    result["stress_net_r"] = (exit_price - price - price * .0065)/risk
    return result


def auc(rows):
    """Rank-pair AUC on cost-after binary labels. None when degenerate."""
    pos = [r["score"] for r in rows if r["primary_net_r"] > 0]
    neg = [r["score"] for r in rows if r["primary_net_r"] <= 0]
    if not pos or not neg:
        return None
    return sum((a > b) + .5 * (a == b) for a in pos for b in neg) / (len(pos)*len(neg))


def metric(rows):
    if not rows:
        return None
    return {"n":len(rows), "positive_rate":sum(r["primary_net_r"] > 0 for r in rows)/len(rows),
            "expectancy_primary_r":sum(r["primary_net_r"] for r in rows)/len(rows),
            "expectancy_stress_r":sum(r["stress_net_r"] for r in rows)/len(rows)}


def evaluate(payload):
    if not isinstance(payload, dict) or payload.get("schema") != "sky-meta-filter-ledger-v0.1":
        raise ValueError("unknown_ledger_schema")
    if payload.get("historical_replay_provenance_verified") is not True:
        raise ValueError("historical_production_replay_not_verified")
    items = payload.get("observations")
    if not isinstance(items, list):
        raise ValueError("missing_observations")
    records = []
    seen = set()
    for obj in items:
        row = validate_observation(obj)
        if row["signal_id"] in seen:
            raise ValueError("duplicate_signal_id")
        seen.add(row["signal_id"])
        records.append(row)
    completed = [x for x in records if x["outcome_status"] == "COUNTERFACTUAL_ONLY"]
    by_day = defaultdict(list)
    for row in completed:
        by_day[row["decision_date"]].append(row)
    top_n = {}
    for n in (3, 5):  # fixed before evaluation, never tune Top N from results
        selected, comparison = [], []
        for day, all_rows in sorted(by_day.items()):
            if len(all_rows) < n:
                continue  # no small-day top-N masquerading as full N
            ranked = sorted(all_rows, key=lambda x: (-x["score"], x["symbol"], x["signal_id"]))
            selected.extend(ranked[:n])
            comparison.extend(all_rows)
        top_n[str(n)] = {
            "selected": metric(selected),
            "same_day_eligible_baseline": metric(comparison),
            "dates": len({r["decision_date"] for r in selected}),
            "not_a_strategy_or_fill": True,
        }
    accepted = [x for x in completed if x["model_decision"] == "ACCEPT"]
    rejected = [x for x in completed if x["model_decision"] == "REJECT"]
    counts = Counter(x["symbol"] for x in completed)
    return {
        "schema": "sky-meta-filter-audit-v0.1",
        "status": RESEARCH_STATUS,
        "production_eligible": False,
        "order_authorized": False,
        "market_data_provenance_independently_verified": False,
        "historical_replay_claim_is_external": True,
        "observations_total":len(records),
        "completed_counterfactual":len(completed),
        "pending":len(records)-len(completed),
        "outcome_completeness":len(completed)/len(records) if records else 0,
        "unique_days":len(by_day),
        "unique_symbols":len(counts),
        "max_symbol_share":max(counts.values())/len(completed) if completed else None,
        "accepted":metric(accepted),
        "rejected":metric(rejected),
        "all_eligible":metric(completed),
        "auc_primary_cost":auc(completed) if completed else None,
        "top_n":top_n,
        "notes":["Retrospective evaluation only; not forward OOS or real executed PnL.",
                 "Candidate and outcome provenance require independent W0/P0-G audit.",
                 "Rejected candidates remain in counterfactual evaluation.",
                 "Never optimize Top N or score threshold on this cohort."],
    }


def main():
    import argparse
    cli = argparse.ArgumentParser()
    cli.add_argument("--input", required=True)
    cli.add_argument("--out", required=True)
    args = cli.parse_args()
    report = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":report["status"],"total":report["observations_total"],
                      "completed":report["completed_counterfactual"],
                      "production_eligible":False},ensure_ascii=False))


if __name__ == "__main__":
    main()
