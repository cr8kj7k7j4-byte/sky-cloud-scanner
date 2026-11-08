"""Research-only chronological portfolio reservation checker.

It enforces *declared* synthetic fill intervals, not fills, dynamic stop
execution, exchange lot rules, market-to-market NAV, or daily kill switches.
Inputs must be prepared independently; no alpha/ranking or actual orders.
"""
from datetime import datetime
from math import isfinite

from research_gate import validate_signal

INITIAL_CASH = 500000.0
MAX_NAMES = 3
MAX_SINGLE_CAPITAL = 100000.0
MAX_SINGLE_RISK = 5000.0
MAX_PORTFOLIO_RISK = 15000.0


def _dt(s):
    if not isinstance(s, str):
        raise ValueError("invalid_exit_timestamp")
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_exit_timestamp") from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("timezone_required")
    return d


def reserve_intervals(records):
    """Return accepted/rejected proposed synthetic intervals.

    Each record follows validate_signal and additionally needs exit_at,
    execution_evidence=SIMULATED, and outcome_source. Positions are released
    at *declared* exit timestamp; cash returns at entry notional for
    diagnostic reservation purposes, not P&L accounting.
    """
    if not isinstance(records, (tuple, list)):
        raise ValueError("records_not_sequence")
    decisions = []
    ids = set()
    for rec in records:
        validate_signal(rec, ids)
        if rec.get("execution_evidence") != "SIMULATED":
            raise ValueError("simulation_only")
        if not isinstance(rec.get("outcome_source"), str) or not rec["outcome_source"].strip():
            raise ValueError("missing_outcome_source")
        if "exit_at" not in rec:
            raise ValueError("missing_exit_at")
        entry_at, exit_at = _dt(rec["decision_at"]), _dt(rec["exit_at"])
        if exit_at <= entry_at:
            raise ValueError("noncausal_exit")
        # Reservation check must never trust an arbitrary declared risk that
        # is smaller than entry-stop exposure, even if signal was prevalidated.
        risk = float(rec["open_risk"])
        capital = float(rec["gross_capital"])
        if not isfinite(risk) or risk <= 0 or risk > MAX_SINGLE_RISK:
            raise ValueError("invalid_trade_risk")
        if not isfinite(capital) or capital <= 0 or capital > MAX_SINGLE_CAPITAL:
            raise ValueError("invalid_trade_capital")
        decisions.append((entry_at, rec["decision_id"], exit_at, rec))
    decisions.sort(key=lambda t: (t[0], t[1]))
    active = []
    accepted, rejected = [], []
    peak_names, peak_risk, peak_capital = 0, 0., 0.
    for entry_at, ident, exit_at, rec in decisions:
        # Existing exits at same instant release before new decisions.
        active = [x for x in active if x["exit_at"] > entry_at]
        capital = sum(x["capital"] for x in active)
        risk = sum(x["risk"] for x in active)
        symbols = {x["symbol"] for x in active}
        new_capital = float(rec["gross_capital"])
        new_risk = float(rec["open_risk"])
        reason = None
        if rec["symbol"] in symbols:
            reason = "SAME_SYMBOL_OVERLAP"
        elif len(active) >= MAX_NAMES:
            reason = "MAX_THREE_NAMES"
        elif capital + new_capital > INITIAL_CASH + 1e-9:
            reason = "CAPITAL_EXCEEDED"
        elif risk + new_risk > MAX_PORTFOLIO_RISK + 1e-9:
            reason = "PORTFOLIO_RISK_EXCEEDED"
        if reason:
            rejected.append({"decision_id": ident, "reason": reason})
            continue
        active.append({"decision_id": ident, "symbol": rec["symbol"],
                       "capital": new_capital, "risk": new_risk,
                       "exit_at": exit_at})
        accepted.append(ident)
        peak_names = max(peak_names, len(active))
        peak_risk = max(peak_risk, risk + new_risk)
        peak_capital = max(peak_capital, capital + new_capital)
    return {
        "accepted_ids": accepted, "rejected": rejected,
        "peak_reserved_names": peak_names,
        "peak_reserved_risk": peak_risk,
        "peak_reserved_capital": peak_capital,
        "status": "INSUFFICIENT_DATA",
        "portfolio_validated": False,
        "actual_execution_validated": False,
        "portfolio_max_drawdown": None,
        "daily_loss_kill_switch_validated": False,
    }
