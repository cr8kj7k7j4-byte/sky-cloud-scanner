"""Offline Swing historical research reader for already-downloaded same-run artifacts.

No network calls or Fugle usage. The caller must independently authenticate
GitHub artifact ZIP digest, run event, run SHA and artifact identity; this
reader validates local content and renders observations only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .swing_postmarket_review import render
from .swing_two_track_acceptance import assess

TPE = ZoneInfo("Asia/Taipei")


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("MISSING_SOURCE_TIME")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_SOURCE_TIME") from exc
    if stamp.tzinfo is None:
        raise ValueError("UNZONED_SOURCE_TIME")
    return stamp.astimezone(TPE)


def read_historical_observation(
    artifact_dir: str | Path,
    readback_receipt: str | Path,
    *,
    expected_run_id: str,
    expected_head_sha: str,
    observed_at: datetime,
    expected_trade_date: str | None = None,
) -> dict:
    """Fail closed until a true independently verified readback is supplied."""
    result = {
        "schema": "SKY_SWING_HISTORICAL_READER_V1",
        "status": "HOLD_EVIDENCE",
        "action": "等待",
        "research_only": True,
        "production_eligible": False,
        "new_entry_authorized": False,
        "source_run_id": expected_run_id,
        "source_head_sha": expected_head_sha,
        "text": None,
        "reason": "HISTORICAL_SOURCE_UNVERIFIED",
    }
    if observed_at.tzinfo is None:
        result["reason"] = "OBSERVATION_TIME_UNZONED"
        return result
    try:
        root = Path(artifact_dir).resolve(strict=True)
        receipt_file = Path(readback_receipt).resolve(strict=True)
        if not root.is_dir() or not receipt_file.is_file():
            raise ValueError("MISSING_ARTIFACT_OR_RECEIPT")
        # Never allow a path through symlinks outside the provided artifact root.
        def read_json(name: str):
            p = (root / name).resolve(strict=True)
            if not p.is_relative_to(root) or not p.is_file():
                raise ValueError("ARTIFACT_PATH_ESCAPE")
            if p.stat().st_size > 15_000_000:
                raise ValueError("ARTIFACT_SIZE_EXCEEDED")
            return json.loads(p.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        scan = read_json("latest_swing.json")
        snapshot = read_json("snapshot_observations_swing.json")
        two_track = read_json("two_track_acceptance.json")
        if not all(isinstance(x, dict) for x in (receipt, scan, snapshot, two_track)):
            raise ValueError("BAD_ARTIFACT_JSON")
        if receipt.get("status") != "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY":
            raise ValueError("MISSING_SUCCESSFUL_INDEPENDENT_RECEIPT")
        if (str(receipt.get("run_id")) != str(expected_run_id)
                or str(receipt.get("head_sha")) != str(expected_head_sha)
                or receipt.get("mode") != "swing"
                or receipt.get("artifact_name") != f"sky-swing-live-{expected_run_id}"
                or not isinstance(receipt.get("artifact_id"), int)):
            raise ValueError("RECEIPT_IDENTITY_MISMATCH")
        if (scan.get("mode") != "swing"
                or scan.get("production_strategy") != "Sky Swing V1.0"
                or scan.get("observations_are_trade_signals") is not False
                or "禁止新進場" not in str(scan.get("trade_decision", ""))):
            raise ValueError("SCAN_POLICY_MISMATCH")
        generated = _parse_time(scan.get("generated_at"))
        reference = observed_at.astimezone(TPE)
        if generated > reference + timedelta(minutes=1):
            raise ValueError("FUTURE_SOURCE_TIME")
        if expected_trade_date and generated.date().isoformat() != expected_trade_date:
            raise ValueError("SOURCE_TRADE_DATE_MISMATCH")
        if receipt.get("data_timestamp") != scan.get("generated_at"):
            raise ValueError("RECEIPT_REPORT_TIME_MISMATCH")
        if (snapshot.get("source") != "Fugle bulk snapshot"
                or _parse_time(snapshot.get("generated_at")).date() != generated.date()):
            raise ValueError("SNAPSHOT_SOURCE_DATE_MISMATCH")
        recalculated = assess(scan, snapshot)
        if recalculated != two_track or recalculated["snapshot_screen_status"] != "PASS_SNAPSHOT_OBSERVATION_ONLY":
            raise ValueError("TWO_TRACK_EVIDENCE_INVALID")
        if (recalculated["production_eligible"] is not False
                or recalculated["candidate_trade_gate"].startswith("HOLD") is not True):
            raise ValueError("TRADE_GATE_INVALID")
        if any(item.get("strategy_signal") is not False
               for item in scan.get("candidates", [])):
            raise ValueError("UNAPPROVED_STRATEGY_SIGNAL")
        if (not isinstance(scan.get("universe_count"), int)
                or scan["universe_count"] <= 0
                or not isinstance(scan.get("quote_count"), int)
                or scan["quote_count"] > scan["universe_count"]
                or scan["quote_count"] < 0):
            raise ValueError("COVERAGE_COUNT_INVALID")
        result.update({
            "status": "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY",
            "action": "觀察",
            "source_trade_date": generated.date().isoformat(),
            "source_timestamp_tpe": generated.isoformat(),
            "snapshot_coverage_pct": scan.get("snapshot_coverage_pct"),
            "verified_quote_coverage_pct": scan.get("quote_coverage_pct"),
            "text": render(scan, snapshot),
            "reason": "RESEARCH_ONLY_NOT_LIVE_OR_ENTRY",
        })
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        result["reason"] = str(exc)[:180]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--trade-date")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = read_historical_observation(
        args.artifact_dir, args.receipt,
        expected_run_id=args.run_id,
        expected_head_sha=args.head_sha,
        expected_trade_date=args.trade_date,
        observed_at=datetime.now(TPE),
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "text"}, ensure_ascii=False))
    if result["status"] != "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY":
        raise SystemExit("HOLD_HISTORICAL_RESEARCH")


if __name__ == "__main__":
    main()
