"""Fail-closed readback of a PAPER_ONLY simulator ledger (never creates fills).

Caller must provide existing simulator artifacts. Matching caller IDs are not
independent proof of the market scan or actual execution quality.
"""
from __future__ import annotations

from datetime import datetime
import math

from research.sky_paper_trade_trace import evaluate_paper_journal


def _aware(value):
    if not isinstance(value, str):
        return None
    try:
        out = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return out if out.utcoffset() is not None else None
    except ValueError:
        return None


def _amount(value, *, integer=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (not integer or float(value).is_integer()))


def audit_paper_ledger(snapshot, journal):
    """Reconcile an external simulator snapshot and its full-day closed fills.

    This is an evidence consistency check, NOT proof that a scan or fill happened.
    """
    errors = []
    if not isinstance(snapshot, dict) or snapshot.get("mode") != "PAPER_ONLY":
        snapshot = {}
        errors.append("PAPER_ONLY_SNAPSHOT_REQUIRED")
    if not isinstance(journal, list):
        journal = []
        errors.append("PAPER_JOURNAL_REQUIRED")
    observed = _aware(snapshot.get("observed_at"))
    if observed is None:
        errors.append("AWARE_SNAPSHOT_TIME_REQUIRED")
    for key in ("run_id", "scan_id", "simulator_version", "source_artifact"):
        if not isinstance(snapshot.get(key), str) or not snapshot[key].strip():
            errors.append("PROVENANCE_" + key.upper() + "_REQUIRED")
    if snapshot.get("journal_scope") != "FULL_DAY":
        errors.append("FULL_DAY_JOURNAL_REQUIRED")
    for key in ("daily_realized_net_pnl_twd", "open_stop_risk_twd",
                "account_equity_twd", "cash_twd", "consecutive_stops", "open_positions"):
        if not _amount(snapshot.get(key), integer=key in ("consecutive_stops", "open_positions")):
            errors.append("INVALID_" + key.upper())
    positions = snapshot.get("positions")
    if not isinstance(positions, list):
        positions = []
        errors.append("POSITIONS_REQUIRED")
    risk = 0.0
    for index, position in enumerate(positions):
        if not isinstance(position, dict):
            errors.append(f"POSITION_{index}_INVALID")
            continue
        if not isinstance(position.get("symbol"), str) or not position["symbol"]:
            errors.append(f"POSITION_{index}_SYMBOL_REQUIRED")
        entry, stop, shares = (position.get(k) for k in ("entry_price", "original_stop", "shares"))
        if not all(_amount(v) and v > 0 for v in (entry, stop, shares)):
            errors.append(f"POSITION_{index}_PRICE_OR_SHARES_INVALID")
            continue
        if stop >= entry or not float(shares).is_integer():
            errors.append(f"POSITION_{index}_STOP_OR_SHARES_INVALID")
            continue
        risk += (entry - stop) * shares
    if _amount(snapshot.get("open_positions"), integer=True) and snapshot["open_positions"] != len(positions):
        errors.append("POSITION_COUNT_MISMATCH")
    if _amount(snapshot.get("open_stop_risk_twd")) and abs(snapshot["open_stop_risk_twd"] - risk) > 0.01:
        errors.append("OPEN_RISK_MISMATCH")
    if _amount(snapshot.get("consecutive_stops"), integer=True) and snapshot["consecutive_stops"] < 0:
        errors.append("NEGATIVE_STOP_COUNT")
    if _amount(snapshot.get("cash_twd")) and snapshot["cash_twd"] < 0:
        errors.append("NEGATIVE_CASH")
    if _amount(snapshot.get("account_equity_twd")) and snapshot["account_equity_twd"] <= 0:
        errors.append("INVALID_EQUITY")
    trace = evaluate_paper_journal(journal)
    if not journal:
        errors.append("NO_SIMULATED_CLOSED_FILLS")
    if trace["paper_journal_status"] != "PAPER_ESTIMATE_RECONCILED_NOT_REAL_EXECUTION":
        errors.append("JOURNAL_NOT_RECONCILED")
    if observed is not None:
        for index, row in enumerate(journal):
            if not isinstance(row, dict):
                continue
            if row.get("market_scan_id") != snapshot.get("scan_id"):
                errors.append(f"FILL_{index}_SCAN_MISMATCH")
            t = _aware(row.get("exit_time"))
            if t and (t > observed or t.date() != observed.date()):
                errors.append(f"FILL_{index}_OUTSIDE_SNAPSHOT_DAY")
    if (trace["paper_net_pnl_estimate_twd"] is not None
            and _amount(snapshot.get("daily_realized_net_pnl_twd"))
            and abs(trace["paper_net_pnl_estimate_twd"] - snapshot["daily_realized_net_pnl_twd"]) > 0.01):
        errors.append("DAILY_NET_PNL_MISMATCH")
    return {
        "schema": "SKY_P0R_PAPER_LEDGER_READBACK_V1",
        "mode": "PAPER_ONLY",
        "snapshot_run_id": snapshot.get("run_id"),
        "scan_id": snapshot.get("scan_id"),
        "source_artifact": snapshot.get("source_artifact"),
        "reconciled": not errors,
        "errors": sorted(set(errors)),
        "paper_fill_count": trace["trade_count"],
        "estimated_net_pnl_twd": trace["paper_net_pnl_estimate_twd"] if not errors else None,
        "paper_cost_arithmetic_reconciled": trace["paper_cost_arithmetic_reconciled"] and not errors,
        "market_source_independently_verified": False,
        "simulated_fill_origin_independently_verified": False,
        "production_eligible": False,
        "live_order_enabled": False,
        "trade_action": "禁止交易",
        "verdict": "EVIDENCE_RECONCILED_ORIGIN_UNVERIFIED" if not errors else "INSUFFICIENT_DATA",
    }


def main():
    """Read ONLY already-created simulator files; never synthesize trades."""
    import json
    from pathlib import Path

    directory = Path("output/sky_paper_runtime")
    snapshot_path = directory / "snapshot.json"
    journal_path = directory / "closed_fills.json"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        snapshot, journal = None, None
    report = audit_paper_ledger(snapshot, journal)
    output = Path("output/sky_p0r_paper_ledger_readback")
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0  # HOLD is an evidence state, not a CI test failure.


if __name__ == "__main__":
    raise SystemExit(main())
