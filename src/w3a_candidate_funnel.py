"""Read-only W3A candidate funnel audit. Never changes trade eligibility."""
from collections import Counter


def build_candidate_funnel(*, universe_count, quote_audit, source,
                           data_gate, working_count, first_pass,
                           top, deep, rejected, unverified, gate_failures):
    """Explain empty candidates without interpreting a data block as no setups.

    All counts are sourced from the same completed scanner execution.
    No market quote, signal or risk context is synthesized here.
    """
    coverage = quote_audit or {}
    source_ok = data_gate == "PASS_FULL_MARKET_LIVE"
    first_n = int(first_pass)
    top_n = int(top)
    deep_n = int(deep)
    rejected_n = int(rejected)
    unverified_n = int(unverified)
    reasons = dict(sorted(Counter(gate_failures).items()))
    if not source_ok:
        cause = "MARKET_DATA_GATE_BLOCKED"
    elif working_count == 0:
        cause = "NO_ELIGIBLE_WORKING_ROWS"
    elif first_n == 0:
        cause = "FIRST_GATE_REJECTED_ALL"
    elif top_n == 0:
        cause = "RANKING_RETURNED_ZERO"
    elif deep_n == 0 and unverified_n:
        cause = "FUGLE_DEEP_DIVE_UNVERIFIED"
    elif deep_n == 0 and rejected_n:
        cause = "DEEP_DIVE_REJECTED_ALL"
    elif deep_n == 0:
        cause = "NO_VERIFIED_DEEP_CANDIDATES"
    else:
        cause = "DEEP_CANDIDATES_PRESENT_NOT_TRADE_APPROVAL"
    return {
        "schema": "SKY_W3A_CANDIDATE_FUNNEL_V1",
        "source": source,
        "data_gate": data_gate,
        "universe_count": int(universe_count),
        "valid_executed_quotes": int(coverage.get("valid_quote_count") or 0),
        "quote_coverage_pct": coverage.get("quote_coverage_pct"),
        "received_by_exchange": coverage.get("received_by_exchange"),
        "missing_by_exchange": coverage.get("missing_by_exchange"),
        "rejected_by_exchange": coverage.get("rejected_by_exchange"),
        "working_rows": int(working_count),
        "first_gate_passed": first_n,
        "first_gate_rejected": max(0, int(working_count) - first_n),
        "first_gate_reasons": reasons,
        "top_ranked": top_n,
        "deep_verified": deep_n,
        "deep_rejected": rejected_n,
        "deep_unverified": unverified_n,
        "zero_candidate_diagnostic": cause,
        "new_trade_approval": False,
        "evidence_scope": "READ_ONLY_SCAN_DIAGNOSTIC",
    }
