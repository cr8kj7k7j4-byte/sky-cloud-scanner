from __future__ import annotations

from copy import deepcopy

CANONICAL_RULE_COLUMNS = (
    "market_gate",
    "sector_rs_gate",
    "multi_timeframe_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "anti_chase_gate",
    "rr_gate",
    "opportunity_ranking_gate",
    "execution_adjustment_gate",
)

PASS_STATUSES = {"FROZEN_CANONICAL_IMPLEMENTATION", "HISTORICAL_SNAPSHOT"}


def build_evidence_preserving_replay_row(
    observed: dict,
    *,
    source_registry: dict,
) -> dict:
    """
    Build a fail-closed replay row without inventing missing v1.4 Alpha logic.

    Observable/PIT-safe fields supplied by upstream data engineering are
    preserved verbatim. Canonical W2 rule columns are populated only when the
    formal frozen-source registry explicitly marks a provider as replay-safe.

    Missing frozen providers => rule value None + BLOCKED status.
    """
    row = deepcopy(observed or {})
    rules = {
        str(x.get("rule")): dict(x)
        for x in (source_registry.get("rules") or [])
        if x.get("rule")
    }

    unresolved = []
    provenance = {}

    for rule in CANONICAL_RULE_COLUMNS:
        meta = rules.get(rule) or {}
        status = str(meta.get("status") or "UNRESOLVED")
        provenance[rule] = {
            "provider_status": status,
            "components": list(meta.get("components") or []),
            "reason": meta.get("reason"),
        }

        # A historical replay may only retain a rule result if:
        # 1) provider provenance is formally allowed; and
        # 2) the row already carries the historical/frozen result.
        if status in PASS_STATUSES and row.get(rule) in (True, False):
            continue

        row[rule] = None
        unresolved.append(rule)

    row["frozen_v14_rule_provenance"] = provenance
    row["frozen_v14_replay_status"] = (
        "PASS" if not unresolved else "FROZEN_ALPHA_INPUT_REQUIRED"
    )
    row["frozen_v14_unresolved_rules"] = unresolved
    row["w2_rule_efficacy_allowed"] = not unresolved
    row["production_change"] = False
    return row


def assert_w2_rule_efficacy_allowed(row: dict) -> None:
    if not bool((row or {}).get("w2_rule_efficacy_allowed")):
        missing = ",".join((row or {}).get("frozen_v14_unresolved_rules") or [])
        raise RuntimeError(
            "W2 rule efficacy blocked: missing frozen v1.4 providers: " + missing
        )
