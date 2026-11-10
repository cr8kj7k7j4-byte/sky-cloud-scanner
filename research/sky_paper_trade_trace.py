"""Traceable PAPER_ONLY journal; calculates hypothetical outcomes only from explicit events.

No broker integration, network access, live trade execution, paper-fill invention,
automated scheduling, or Production promotion.
"""
from __future__ import annotations
from datetime import datetime
import math


REQUIRED = ("paper_trade_id", "signal_id", "market_scan_id",
            "market_data_time", "entry_time", "exit_time", "symbol",
            "entry_price", "exit_price", "shares", "entry_fee_twd",
            "exit_fee_twd", "sale_tax_twd", "slippage_estimate_twd",
            "spread_estimate_twd", "liquidity_impact_estimate_twd",
            "fill_assumption", "source_type")


def _time(v):
    try:
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v if v.utcoffset() is not None else None
    except (TypeError, ValueError, AttributeError):
        return None


def _positive(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def _non_negative(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def evaluate_paper_journal(entries):
    """Return auditable estimated paper P&L, not real fill quality/profitability."""
    report = {
        "schema": "SKY_PAPER_TRADE_TRACE_V1",
        "mode": "PAPER_ONLY",
        "live_trading_enabled": False,
        "broker_ledger_required": False,
        "trade_count": 0,
        "paper_net_pnl_estimate_twd": None,
        "after_cost_paper_performance_verified": False,
        "market_scan_source_verified": False,
        "paper_cost_arithmetic_reconciled": False,
        "real_execution_quality_verified": False,
        "paper_journal_status": "INSUFFICIENT_DATA",
        "rows": [],
        "rejected": [],
        "no_live_trade": True,
    }
    if not isinstance(entries, list) or not entries:
        return report
    ids = set()
    net = 0.0
    for idx, row in enumerate(entries):
        problems = []
        if not isinstance(row, dict):
            report["rejected"].append({"index": idx, "reasons": ["INVALID_ROW"]})
            continue
        for field in REQUIRED:
            if field not in row or row[field] is None or row[field] == "":
                problems.append("MISSING_" + field.upper())
        for field in ("paper_trade_id", "signal_id", "market_scan_id", "symbol"):
            if field in row and not isinstance(row[field], str):
                problems.append("INVALID_" + field.upper())
        key = row.get("paper_trade_id")
        if isinstance(key, str):
            if key in ids:
                problems.append("DUPLICATE_PAPER_TRADE_ID")
            ids.add(key)
        if row.get("source_type") != "PAPER_SIMULATION":
            problems.append("NOT_EXPLICIT_PAPER_EVENT")
        if row.get("fill_assumption") not in ("NEXT_BAR_OPEN_ESTIMATE", "LIMIT_TOUCH_ESTIMATE"):
            problems.append("UNSUPPORTED_FILL_ASSUMPTION")
        timestamps = [_time(row.get(x)) for x in ("market_data_time", "entry_time", "exit_time")]
        if None in timestamps:
            problems.append("INVALID_AWARE_TIMESTAMPS")
        elif not timestamps[0] <= timestamps[1] < timestamps[2]:
            problems.append("INVALID_TEMPORAL_CAUSALITY")
        for f in ("entry_price", "exit_price", "shares"):
            if not _positive(row.get(f)):
                problems.append("INVALID_" + f.upper())
        if _positive(row.get("shares")) and not float(row["shares"]).is_integer():
            problems.append("INVALID_SHARE_COUNT")
        for f in ("entry_fee_twd", "exit_fee_twd", "sale_tax_twd",
                  "slippage_estimate_twd", "spread_estimate_twd",
                  "liquidity_impact_estimate_twd"):
            if not _non_negative(row.get(f)):
                problems.append("INVALID_" + f.upper())
        if problems:
            report["rejected"].append({"index": idx, "paper_trade_id": key,
                                        "reasons": sorted(set(problems))})
            continue
        shares = int(row["shares"])
        gross = (row["exit_price"]-row["entry_price"]) * shares
        costs = sum(row[f] for f in ("entry_fee_twd", "exit_fee_twd", "sale_tax_twd",
                                     "slippage_estimate_twd", "spread_estimate_twd",
                                     "liquidity_impact_estimate_twd"))
        estimate = gross - costs
        net += estimate
        report["rows"].append({
            "paper_trade_id": key, "symbol": row["symbol"],
            "signal_id": row["signal_id"], "market_scan_id": row["market_scan_id"],
            "market_data_time": row["market_data_time"],
            "entry_time": row["entry_time"], "exit_time": row["exit_time"],
            "shares": shares, "entry_price": row["entry_price"],
            "exit_price": row["exit_price"], "fill_assumption": row["fill_assumption"],
            "gross_pnl_twd": round(gross, 4), "assumed_cost_twd": round(costs, 4),
            "net_pnl_estimate_twd": round(estimate, 4), "source_type": "PAPER_SIMULATION",
            "real_fill": False})
    report["trade_count"] = len(report["rows"])
    # Reject partial journals instead of reporting incomplete aggregates as valid.
    if report["rejected"] or len(report["rows"]) != len(entries):
        report["paper_journal_status"] = "REJECTED_INCOMPLETE_OR_INVALID"
        return report
    report["paper_net_pnl_estimate_twd"] = round(net, 4)
    report["paper_journal_status"] = "PAPER_ESTIMATE_RECONCILED_NOT_REAL_EXECUTION"
    report["paper_cost_arithmetic_reconciled"] = True
    # IDs are caller supplied: no independent source/observed fill proof yet.
    report["after_cost_paper_performance_verified"] = False
    return report
