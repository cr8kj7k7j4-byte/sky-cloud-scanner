"""Read-only P0-L/W4 identity and outcome reconciliation; never creates trades.

Observation IDs are not approved strategy decision IDs. Counterfactual outcomes
must not become realized P&L without separately verified execution evidence.
"""
from collections import Counter
from datetime import datetime
from math import isfinite


def _timestamp(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def _number(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        return isfinite(float(value))
    except (ValueError, TypeError):
        return False


def reconcile_decision_outcomes(records):
    """Return checkable counts; do not treat ranking or paper as actual trades."""
    rows = [x for x in (records or []) if isinstance(x, dict)]
    reasons = Counter()
    seen = {}
    duplicate_rows = 0
    conflicting_duplicates = 0
    observations = 0
    source_backed_decisions = 0
    linked_outcomes = 0
    verified_fills = 0
    for row in rows:
        rid = str(row.get("record_id") or "").strip()
        obs_id = str(row.get("observation_record_id") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        observed = str(row.get("observed_at") or "").strip()
        if not rid:
            reasons["MISSING_RECORD_ID"] += 1
            continue
        identity = (symbol, observed, str(row.get("run_id") or ""))
        if rid in seen:
            duplicate_rows += 1
            if seen[rid] != identity:
                conflicting_duplicates += 1
                reasons["CONFLICTING_RECORD_ID"] += 1
            continue
        seen[rid] = identity
        if not symbol or _timestamp(observed) is None:
            reasons["INVALID_OBSERVATION_IDENTITY"] += 1
            continue
        if obs_id == rid and row.get("decision_provenance_status") == "RANKING_OBSERVATION_ONLY":
            observations += 1
        else:
            reasons["UNVERIFIED_OBSERVATION_PROVENANCE"] += 1

        decision_id = row.get("decision_id")
        if decision_id is None:
            reasons["NO_APPROVED_STRATEGY_DECISION_ID"] += 1
            continue

        # This read-only audit has no W0/P0-G-approved decision-source adapter.
        # A caller-supplied decision_id alone can never satisfy this gate.
        reasons["STRATEGY_DECISION_SOURCE_NOT_CERTIFIED"] += 1
        outcome = row.get("outcome") or {}
        if not isinstance(outcome, dict):
            reasons["INVALID_OUTCOME"] += 1
            continue
        if outcome.get("decision_id") != decision_id:
            reasons["OUTCOME_DECISION_ID_MISMATCH"] += 1
            continue
        if outcome.get("outcome_type") in {"SHADOW_EVIDENCE", "COUNTERFACTUAL_SHADOW"}:
            reasons["COUNTERFACTUAL_NOT_ACTUAL"] += 1
            continue
        execution = row.get("execution") or {}
        if not isinstance(execution, dict):
            reasons["INVALID_EXECUTION"] += 1
            continue
        if (
            execution.get("evidence_type") == "ACTUAL_EXECUTION"
            and execution.get("fill_status") in {"FILLED", "PARTIAL"}
            and _number(execution.get("fill_price"))
            and _timestamp(execution.get("fill_timestamp"))
            and execution.get("fill_source")
        ):
            verified_fills += 1
            linked_outcomes += 1
        else:
            reasons["ACTUAL_FILL_EVIDENCE_MISSING"] += 1

    return {
        "schema": "P0L_W4_DECISION_OUTCOME_RECONCILIATION_V1",
        "status": "HOLD_PENDING_APPROVED_DECISION_SOURCE",
        "rows_loaded": len(rows),
        "unique_record_ids": len(seen),
        "duplicate_rows": duplicate_rows,
        "conflicting_duplicates": conflicting_duplicates,
        "ranking_observations": observations,
        "approved_strategy_decisions": source_backed_decisions,
        "verified_fill_candidates_not_promotable": verified_fills,
        "linked_outcome_candidates_not_promotable": linked_outcomes,
        "eligible_strategy_trades": 0,
        "realized_net_pnl": None,
        "cost_adjusted_expectancy_r": None,
        "reasons": dict(sorted(reasons.items())),
        "production_eligible": False,
        "note": "Observation IDs and source-unverified decision IDs are not approved trades; actual executions require W0/P0-G provenance review.",
    }
