"""Fail-closed W4 evidence integrity counters (research/report only).

Ranking observations, rule-eligible counterfactuals, modelled costs and observed
fills are separate; this module never turns ranking records into trade results.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from math import isfinite

LEDGER_START = datetime.fromisoformat("2026-10-24T23:28:08+00:00")
REQUIRED_COST_FIELDS = ("fee_rate_per_side", "sell_tax_rate", "entry_impact_rate", "exit_impact_rate")


def _valid_number(value):
    if value is None or isinstance(value, bool):
        return False
    try:
        return isfinite(float(value))
    except (ValueError, TypeError):
        return False


def _observed_at(value):
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(timezone.utc)


def audit_forward_strategy_evidence(records):
    """Audit without silently upgrading counterfactuals to actual executions.

    Modelled cost completeness is distinct from observed L1 execution evidence.
    A quote or assumed trigger price never proves a fill.
    """
    rows = [row for row in (records or []) if isinstance(row, dict)]
    reasons = Counter()
    eligible = modeled_complete = full_outcome = observed_fills = 0
    valid_rows = 0
    unknown_regime_rows = 0

    for row in rows:
        observed = _observed_at(row.get("observed_at") or row.get("observation_timestamp"))
        if observed is None or observed < LEDGER_START:
            reasons["missing_or_preledger_timestamp"] += 1
            continue
        if not str(row.get("symbol") or "").strip():
            reasons["missing_symbol"] += 1
            continue
        valid_rows += 1
        regime = (row.get("research_context") or {}).get("regime")
        if regime is None or str(regime).upper().startswith("UNKNOWN"):
            unknown_regime_rows += 1
        monitor = row.get("monitor") or {}
        risk = row.get("risk") or {}
        strategy = row.get("strategy") or {}
        checks = {
            "monitor_not_triggered": monitor.get("state") != "TRIGGERED",
            "risk_not_allow": risk.get("status") != "ALLOW",
            "trigger_missing": not _valid_number(strategy.get("trigger")),
            "stop_missing": not _valid_number(strategy.get("stop")),
            "target_missing": not _valid_number(strategy.get("target")),
        }
        missing = [name for name, failed in checks.items() if failed]
        if missing:
            reasons.update(missing)
            continue

        eligible += 1
        result = (row.get("outcome") or {}).get("strategy_counterfactual") or {}
        if result.get("status") != "COMPLETE" or not _valid_number(result.get("r_multiple")):
            reasons["strategy_outcome_not_complete"] += 1
            continue

        assumptions = result.get("cost_assumptions") or {}
        missing_costs = [field for field in REQUIRED_COST_FIELDS
                         if not _valid_number(assumptions.get(field))]
        if not str(result.get("execution_cost_profile") or "").strip():
            missing_costs.append("execution_cost_profile")
        if missing_costs:
            reasons.update("missing_cost_" + field for field in missing_costs)
            continue

        modeled_complete += 1
        full_outcome += 1
        # Only source-backed actual fills count here. Shadow/counterfactual
        # records always remain non-executed regardless of their modeled R.
        execution = row.get("execution") or {}
        if (
            execution.get("evidence_type") == "ACTUAL_EXECUTION"
            and execution.get("fill_status") in {"FILLED", "PARTIAL"}
            and _valid_number(execution.get("fill_price"))
            and _observed_at(execution.get("fill_timestamp")) is not None
            and str(execution.get("fill_source") or "").strip()
        ):
            observed_fills += 1

    return {
        "schema_version": "W4_STRATEGY_EVIDENCE_INTEGRITY_V1",
        "status": "INSUFFICIENT_DATA" if not full_outcome else "OBSERVATIONS_PRESENT",
        "ranking_rows_loaded": len(rows),
        "post_ledger_valid_rows": valid_rows,
        "eligible_strategy_records": eligible,
        "complete_strategy_outcomes_with_modelled_costs": full_outcome,
        "modelled_cost_complete_ratio": round(modeled_complete / eligible, 6) if eligible else 0.0,
        "observed_execution_fills": observed_fills,
        "observed_execution_fill_ratio": round(observed_fills / eligible, 6) if eligible else 0.0,
        "unknown_regime_rows": unknown_regime_rows,
        "reasons": dict(sorted(reasons.items())),
        "production_eligible": False,
        "note": "Modelled costs and counterfactual R are not L1 observed slippage, actual fills or realized PnL. Unknown regimes do not prove bull/neutral/bear coverage."
    }
