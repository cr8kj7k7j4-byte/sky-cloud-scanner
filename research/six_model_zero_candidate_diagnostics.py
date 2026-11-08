"""Read-only six-model candidate funnel diagnostics. Never generates trade signals.

Each record is independently reported; a UI label alone does not prove a deployed model.
The caller must supply real stage counts and execution provenance.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

STAGES = (
    "universe", "market_data", "valid_executed_trades",
    "model_inputs", "research_candidates", "ledger_readback",
    "mobile_visible", "trade_candidates",
)
FAIL_STATES = {"DATA_ERROR", "DATA_STALE", "MODEL_ERROR", "LEDGER_ERROR", "NOT_DEPLOYED"}


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def diagnose(record: dict, *, market_open: bool) -> dict:
    """Classify zero candidates without substituting a missing counter with zero."""
    name = str(record.get("ui_name") or "UNKNOWN")
    base = {"ui_name": name, "model_id": record.get("model_id"),
            "model_version": record.get("model_version"), "status": "NOT_DEPLOYED",
            "reason": "MODEL_ID_OR_RUN_MISSING", "counts": {}, "trade_authorized": False}
    if not record.get("model_id") or not record.get("model_version") or not record.get("run_id"):
        return base
    counts = {key: record.get(key) for key in STAGES}
    base["counts"] = counts
    if any(type(value) is not int or value < 0 for value in counts.values()):
        return {**base, "status": "DATA_ERROR", "reason": "MISSING_OR_INVALID_FUNNEL_COUNTER"}
    if any(counts[right] > counts[left] for left, right in zip(STAGES, STAGES[1:])):
        # Counters must describe an explicitly nested funnel, not unrelated model populations.
        return {**base, "status": "DATA_ERROR", "reason": "FUNNEL_COUNT_INCREASED"}
    run_at, data_at = _time(record.get("run_at")), _time(record.get("source_timestamp"))
    if run_at is None or data_at is None or data_at > run_at:
        return {**base, "status": "DATA_ERROR", "reason": "INVALID_TIMESTAMP_PROVENANCE"}
    if record.get("model_error"):
        return {**base, "status": "MODEL_ERROR", "reason": "MODEL_RUNTIME_ERROR"}
    if record.get("ledger_error"):
        return {**base, "status": "LEDGER_ERROR", "reason": "LEDGER_WRITE_READBACK_FAILED"}
    if counts["market_data"] == 0 or counts["valid_executed_trades"] == 0:
        return {**base, "status": "DATA_ERROR" if market_open else "MARKET_CLOSED",
                "reason": "NO_VALID_MARKET_DATA"}
    if market_open and (run_at - data_at).total_seconds() > 300:
        return {**base, "status": "DATA_STALE", "reason": "QUOTE_OLDER_THAN_300_SECONDS"}
    if not record.get("model_completed"):
        return {**base, "status": "MODEL_ERROR", "reason": "MODEL_NOT_COMPLETED"}
    if counts["model_inputs"] == 0:
        return {**base, "status": "DATA_ERROR", "reason": "NO_MODEL_INPUTS"}
    if counts["research_candidates"] > counts["ledger_readback"]:
        return {**base, "status": "LEDGER_ERROR", "reason": "RESEARCH_CANDIDATES_NOT_READ_BACK"}
    if counts["ledger_readback"] > counts["mobile_visible"]:
        return {**base, "status": "LEDGER_ERROR", "reason": "MOBILE_API_MISSING_LEDGER_ROWS"}
    if not market_open:
        return {**base, "status": "MARKET_CLOSED", "reason": "LAST_SESSION_DIAGNOSTIC_ONLY"}
    if counts["research_candidates"] == 0:
        if not record.get("rejection_reasons"):
            return {**base, "status": "DATA_ERROR", "reason": "NO_CANDIDATES_WITHOUT_REJECTION_AUDIT"}
        return {**base, "status": "NO_SIGNAL", "reason": "AUDITED_MODEL_REJECTIONS"}
    return {**base, "status": "HEALTHY", "reason": "RESEARCH_CANDIDATES_AUDITED"}


def diagnose_all(records: list[dict], *, market_open: bool) -> dict:
    rows = [diagnose(row, market_open=market_open) for row in records]
    ids = [row["model_id"] for row in rows if row["model_id"]]
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    return {
        "schema": "SKY_SIX_MODEL_FUNNEL_DIAGNOSTIC_V1",
        "status": "FAIL_CLOSED" if duplicates or any(r["status"] in FAIL_STATES for r in rows)
                  else "OBSERVATION_ONLY",
        "duplicate_model_ids": duplicates,
        "models_received": len(rows),
        "models_with_verified_identity": sum(bool(r["model_id"] and r["model_version"])
                                               for r in rows),
        "models": rows,
        "production_promotion_eligible": False,
        "notice": "Inputs must be genuine runner evidence; no simulated market prices or trade signals.",
    }
