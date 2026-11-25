"""W0 #363 Plan A: independent, read-only A1/A2 evidence from the SAME scan.

No provider calls, new strategy eligibility, orders, or whole-market gate changes.
Missing, mismatched or malformed files remain HOLD, not PASS.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
OBSERVATION = "PASS_SNAPSHOT_OBSERVATION_ONLY"
EXECUTION = "PASS_BOUNDED_INDIVIDUAL_EXECUTION_ONLY"


def _clock(value):
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.astimezone(TPE) if stamp.utcoffset() is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _a1(report):
    if not isinstance(report, dict) or report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        return "HOLD_MISSING_OR_INVALID_SNAPSHOT_REPORT"
    checked = _clock(report.get("checked_at_tpe"))
    all_rows = report.get("all_symbols")
    count = report.get("universe_count")
    if (checked is None or type(count) is not int or count <= 0
            or not isinstance(all_rows, list) or len(all_rows) != count
            or report.get("no_order_or_production_promotion") is not True):
        return "HOLD_UNVERIFIED_SNAPSHOT_UNIVERSE"
    markets = report.get("by_exchange") or {}
    integrity = report.get("snapshot_integrity") or {}
    seen = set()
    counted = {"TWSE": {"total": 0, "observed": 0},
               "TPEx": {"total": 0, "observed": 0}}
    for row in all_rows:
        if not isinstance(row, dict) or row.get("exchange") not in counted:
            return "HOLD_INVALID_SNAPSHOT_ROW"
        key = (row["exchange"], str(row.get("symbol") or ""))
        if not key[1] or key in seen or row.get("production_eligible") is not False:
            return "HOLD_DUPLICATE_OR_UNSAFE_SNAPSHOT_ROW"
        seen.add(key)
        counted[key[0]]["total"] += 1
        if (row.get("source") == "Fugle paid bulk snapshot"
                and row.get("snapshot_source_date") == checked.date().isoformat()
                and row.get("snapshot_is_trial") is not True
                and isinstance(row.get("last_price"), (int, float))
                and not isinstance(row["last_price"], bool) and 0 < row["last_price"] < float("inf")):
            counted[key[0]]["observed"] += 1
    if (sum(x["observed"] for x in counted.values()) != report.get("observed_price_count")
            or sum(x["total"] for x in counted.values()) != count):
        return "HOLD_SNAPSHOT_COUNT_MISMATCH"
    for exchange in counted:
        market = markets.get(exchange) or {}
        audit = integrity.get(exchange) or {}
        total, observed = counted[exchange]["total"], counted[exchange]["observed"]
        if (total <= 0 or market.get("universe") != total
                or market.get("observed_price") != observed
                or audit.get("api_response_valid") is not True
                or audit.get("snapshot_time_is_execution_time") is not False
                or audit.get("snapshot_date") != checked.date().isoformat()
                or not 100 * observed / total >= 70):
            return "HOLD_SNAPSHOT_MARKET_SOURCE_OR_COVERAGE"
    if 100 * report["observed_price_count"] / count < 80:
        return "HOLD_SNAPSHOT_TOTAL_COVERAGE"
    return OBSERVATION


def _a2(report, probe):
    if not isinstance(probe, dict) or probe.get("schema") != "SKY_FUGLE_INDIVIDUAL_EXECUTION_PROBE_V1":
        return "HOLD_MISSING_OR_INVALID_CANDIDATE_QUOTE_REPORT"
    if (probe.get("production_eligible") is not False
            or probe.get("full_market_executed_certified") is not False
            or probe.get("source") != "Fugle paid /intraday/quote only"):
        return "HOLD_CANDIDATE_SOURCE_OR_SAFETY_FLAG"
    origin = _clock(report.get("checked_at_tpe")) if isinstance(report, dict) else None
    stamp = _clock(probe.get("checked_at_tpe"))
    if (origin is None or stamp is None or stamp.date() != origin.date()
            or not 0 <= (stamp - origin).total_seconds() <= 600
            or probe.get("snapshot_checked_at_tpe") != report.get("checked_at_tpe")):
        return "HOLD_CANDIDATE_SOURCE_TIME_MISMATCH"
    rows = probe.get("rows")
    n = probe.get("requested_count")
    if (not isinstance(rows, list) or type(n) is not int or not 1 <= n <= 8
            or len(rows) != n):
        return "HOLD_CANDIDATE_COUNT_MISMATCH"
    pool = {(r.get("exchange"), str(r.get("symbol"))) for r in report.get("ranked_observations", [])
            if isinstance(r, dict) and r.get("source") == "Fugle paid bulk snapshot"}
    seen = set()
    valid = 0
    for row in rows:
        if not isinstance(row, dict):
            return "HOLD_INVALID_CANDIDATE_ROW"
        key = (row.get("exchange"), str(row.get("symbol")))
        if (key not in pool or key in seen or row.get("production_eligible") is not False
                or row.get("source") != "Fugle paid individual /intraday/quote"):
            return "HOLD_CANDIDATE_NOT_FROM_A1_OR_UNSAFE"
        seen.add(key)
        if row.get("status") == "FRESH_EXECUTED_TRADE":
            price, ts = row.get("latest_executed_price"), _clock(row.get("last_trade_time"))
            if (not isinstance(price, (float, int)) or isinstance(price, bool)
                    or not 0 < price < float("inf") or ts is None or ts.date() != stamp.date()
                    # A2 acceptance is a point-in-time report: no future execution\n                    # may be certified even if the lower-level quote parser\n                    # allows a small clock-skew tolerance.\n                    or not 0 <= (stamp - ts).total_seconds() <= 180):
                return "HOLD_INVALID_LAST_TRADE_PRICE_TIME"
            valid += 1
    if probe.get("verified_fresh_executed_count") != valid:
        return "HOLD_CANDIDATE_VERIFIED_COUNT_MISMATCH"
    return EXECUTION if valid else "HOLD_NO_FRESH_CANDIDATE_EXECUTION"


def assess(whole, probe, operational, *, run_id=None, run_attempt=None, head_sha=None, event=None):
    """A1 and A2 have separate statuses; original whole-market gate is untouched."""
    a1 = _a1(whole)
    a2 = _a2(whole, probe)
    op = operational if isinstance(operational, dict) else {}
    gate = op.get("live_market_evidence") or {}
    # Report only the ORIGINAL operational result. It is never promoted by A1/A2.
    original_ok = (op.get("operational_full_market_scan") is True
                   and gate.get("valid_whole_market_operational") is True
                   and op.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
                   and op.get("market_data_gate") == "PASS_FULL_MARKET_LIVE")
    return {
        "schema": "SKY_INTRADAY_PLAN_A_TWO_TRACK_ACCEPTANCE_V1",
        "run_id": run_id, "run_attempt": run_attempt, "head_sha": head_sha, "event_name": event,
        "snapshot_screen_status": a1,
        "candidate_execution_status": a2,
        "full_market_execution_status": ("PASS_ORIGINAL_FULL_MARKET_GATE" if original_ok
                                         else "HOLD_ORIGINAL_FULL_MARKET_EXECUTION_GATE"),
        "a1_observation_only": True, "a2_candidate_only": True,
        "full_market_gate_promoted_by_a1_or_a2": False,
        "candidate_trade_gate": "HOLD_FIVE_MIN_VWAP_COST_RISK_AND_STRATEGY_NOT_CERTIFIED",
        "production_eligible": False, "automatic_order": False, "trade_action": "禁止交易",
        "note": "A1 snapshot observation != A2 individual execution != full-market execution != strategy approval.",
    }


def main():
    root = Path("output/sky_quickscan_information")
    def read(path):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, ValueError, UnicodeError):
            return None
    receipt = assess(
        read(root / "full_universe.json"),
        read(root / "fugle_execution_samples.json"),
        read("output/latest.json"),
        run_id=os.environ.get("GITHUB_RUN_ID"),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        head_sha=os.environ.get("GITHUB_SHA"),
        event=os.environ.get("GITHUB_EVENT_NAME"),
    )
    root.mkdir(parents=True, exist_ok=True)
    path = root / "intraday_plan_a_two_track_acceptance.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PLAN_A_A1:", receipt["snapshot_screen_status"])
    print("PLAN_A_A2:", receipt["candidate_execution_status"])
    print("PLAN_A_FULL_MARKET:", receipt["full_market_execution_status"])
    print("PLAN_A_ACTION: 禁止交易")


if __name__ == "__main__":
    main()
