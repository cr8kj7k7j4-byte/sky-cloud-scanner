"""Publish a truthful W1 live-scan outcome, not a green stale-history run."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def validate_swing_scan_output(payload: dict) -> dict:
    guard = payload.get("signal_date_guard") or {}
    status = guard.get("status")
    fresh = guard.get("fresh") is True
    signal_date = payload.get("signal_date")
    expected = guard.get("expected_signal_date")
    valid = fresh and status == "PASS" and bool(signal_date) and signal_date == expected
    return {
        "status": "PASS" if valid else "BLOCKED_STALE_SIGNAL_HISTORY",
        "signal_date": payload.get("signal_date"),
        "expected_signal_date": guard.get("expected_signal_date"),
        "guard_status": status,
        "candidate_count": payload.get("candidate_count"),
        "publication_allowed": valid,
        "production_eligible": False,
        "reason": "A historical V1.1 candidate scan is not valid without the previous verified trading-day D-close signal.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    x = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = validate_swing_scan_output(x)
    p=Path(args.report)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    if out["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
