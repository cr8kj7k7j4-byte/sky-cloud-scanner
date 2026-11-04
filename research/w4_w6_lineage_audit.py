"""Read-only fail-closed W4↔W6 observation/attempt lineage audit.

This never fabricates execution or modifies trading rules.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone

from research.w6_execution_attempts import validate_attempt


def _timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _identity(row):
    decision_id = str(row.get("decision_id") or "").strip()
    run_id = str(row.get("run_id") or "").strip()
    symbol = str(row.get("symbol") or "").strip()
    observed = _timestamp(row.get("observation_timestamp") or row.get("observed_at"))
    if not all((decision_id, run_id, symbol, observed)):
        return None
    return decision_id, run_id, symbol, observed


def audit_forward_execution_joins(paper_records, attempts):
    """Counts only verifiable, unambiguous, point-in-time execution attempts.

    A valid W6 attempt is not a fill unless separately confirmed with an
    authorized execution source; missing identity is never inferred.
    """
    paper = {}
    paper_duplicates = set()
    for row in paper_records or []:
        if not isinstance(row, dict):
            continue
        key = _identity(row)
        if key is None:
            continue
        if key in paper:
            paper_duplicates.add(key)
        else:
            paper[key] = row

    reasons = Counter()
    accepted = 0
    confirmed = 0
    seen_attempt_ids = set()
    for row in attempts or []:
        if not isinstance(row, dict):
            reasons["invalid_attempt_object"] += 1
            continue
        attempt_id = str(row.get("attempt_id") or "").strip()
        if attempt_id in seen_attempt_ids:
            reasons["duplicate_attempt_id"] += 1
            continue
        if attempt_id:
            seen_attempt_ids.add(attempt_id)

        errors = validate_attempt(row)
        if errors:
            reasons["invalid_w6_attempt"] += 1
            continue
        key = _identity(row)
        if key is None:
            reasons["missing_join_identity"] += 1
            continue
        if key in paper_duplicates:
            reasons["ambiguous_paper_identity"] += 1
            continue
        matched = paper.get(key)
        if matched is None:
            reasons["unmatched_paper_decision"] += 1
            continue

        attempt_at = _timestamp(row.get("execution_attempt_timestamp"))
        if attempt_at is None or attempt_at < key[3]:
            reasons["invalid_attempt_sequence"] += 1
            continue
        if str(row.get("strategy_version") or "") != str(matched.get("strategy_version") or "") or not row.get("strategy_version"):
            reasons["strategy_version_mismatch"] += 1
            continue
        if row.get("fill_status") in {"FILLED", "PARTIAL"}:
            fill_at = _timestamp(row.get("fill_timestamp"))
            if fill_at is None or fill_at < attempt_at:
                reasons["invalid_fill_sequence"] += 1
                continue
        accepted += 1
        if (row.get("fill_status") in {"FILLED", "PARTIAL"}
            and row.get("source_type") in {"BROKER_EXECUTION", "AUTHORIZED_PAPER_ENGINE"}):
            confirmed += 1

    return {
        "schema_version": "W4_W6_LINEAGE_AUDIT_V1",
        "valid_paper_identities": len(paper) - len(paper_duplicates),
        "ambiguous_paper_identities": len(paper_duplicates),
        "attempts_seen": len(attempts or []),
        "verified_joined_attempts": accepted,
        "source_backed_fills": confirmed,
        "rejected_reasons": dict(sorted(reasons.items())),
        "status": "PASS" if accepted else "INSUFFICIENT_DATA",
        "production_eligible": False,
        "note": "Join evidence is research-only. Unknown or quote-only attempts never imply a fill.",
    }
