"""W6 research-only explicit execution-attempt evidence.

Does not submit orders, infer fills, or alter Production gates.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

FINAL = {"FILLED", "PARTIAL", "MISSED", "CANCELLED", "REJECTED"}
FILLS = {"FILLED", "PARTIAL"}


def _dt(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo is not None else None


def validate_attempt(attempt: dict) -> list[str]:
    """Fail closed: a quote snapshot cannot stand in for an attempted order."""
    a = dict(attempt or {})
    errors = []
    for field in ("attempt_id", "decision_id", "symbol", "execution_type",
                  "source", "observation_timestamp", "execution_attempt_timestamp"):
        if not a.get(field):
            errors.append("MISSING_" + field.upper())
    for field in ("observation_timestamp", "execution_attempt_timestamp"):
        if a.get(field) and _dt(a[field]) is None:
            errors.append("INVALID_" + field.upper())
    obs = _dt(a.get("observation_timestamp"))
    sent = _dt(a.get("execution_attempt_timestamp"))
    if obs and sent and sent < obs:
        errors.append("ATTEMPT_BEFORE_OBSERVATION")
    status = a.get("fill_status", "UNKNOWN")
    if status not in FINAL | {"UNKNOWN"}:
        errors.append("INVALID_FILL_STATUS")
    price = a.get("fill_price")
    filled_at = _dt(a.get("fill_timestamp"))
    if status in FILLS:
        if price is None or not isinstance(price, (int, float)) or price <= 0:
            errors.append("VALID_FILL_PRICE_REQUIRED")
        if filled_at is None:
            errors.append("VALID_FILL_TIMESTAMP_REQUIRED")
        if sent and filled_at and filled_at < sent:
            errors.append("FILL_BEFORE_ATTEMPT")
        shares = a.get("filled_shares")
        if not isinstance(shares, int) or shares <= 0:
            errors.append("POSITIVE_FILLED_SHARES_REQUIRED")
        requested = a.get("requested_shares")
        if isinstance(requested, int) and requested > 0 and isinstance(shares, int) and shares > requested:
            errors.append("OVERFILLED")
    else:
        if price is not None or a.get("fill_timestamp") is not None or a.get("filled_shares") not in (None, 0):
            errors.append("NON_FILL_CANNOT_HAVE_FILL_DATA")
    if status in FINAL and a.get("source_type") not in {"BROKER_EXECUTION", "AUTHORIZED_PAPER_ENGINE"}:
        errors.append("FINAL_FILL_STATUS_REQUIRES_AUTHORIZED_EXECUTION_SOURCE")
    if a.get("source_type") == "AUTHORIZED_PAPER_ENGINE" and a.get("paper_gate_verdict") != "PASS_TO_PAPER_TRADING":
        errors.append("PAPER_GATE_NOT_PASSED")
    if a.get("source_type") == "BROKER_EXECUTION" and not a.get("broker_execution_id"):
        errors.append("BROKER_EXECUTION_ID_REQUIRED")
    if a.get("research_only") is not True:
        errors.append("RESEARCH_ONLY_REQUIRED")
    return errors


def ingest_attempts(input_jsonl: str | Path, output_jsonl: str | Path) -> dict:
    """Validate externally supplied attempts; refuse to write any invalid row."""
    accepted, rejected = [], []
    path = Path(input_jsonl)
    if not path.exists():
        return {"accepted": 0, "rejected": 0, "status": "NO_EXECUTION_SOURCE"}
    seen = set()
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError("row must be object")
        except (ValueError, json.JSONDecodeError):
            rejected.append({"line": index, "errors": ["INVALID_JSON"]})
            continue
        errors = validate_attempt(row)
        if row.get("attempt_id") in seen:
            errors.append("DUPLICATE_ATTEMPT_ID")
        if errors:
            rejected.append({"line": index, "errors": errors})
        else:
            seen.add(row["attempt_id"])
            accepted.append(row)
    dest = Path(output_jsonl)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in accepted), encoding="utf-8")
    return {
        "accepted": len(accepted), "rejected": len(rejected),
        "status": "READY" if accepted else "INSUFFICIENT_DATA",
        "errors": rejected,
        "research_only": True,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="research_output/w6_verified_attempts.jsonl")
    args = parser.parse_args()
    print(json.dumps(ingest_attempts(args.input, args.output), ensure_ascii=False, indent=2))
