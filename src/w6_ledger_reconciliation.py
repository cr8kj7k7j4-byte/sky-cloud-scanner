"""W6: read-only reconciliation of externally supplied trade/position evidence.

This module NEVER certifies broker provenance. It derives risk figures from
transaction-level rows for review, and ALWAYS holds live admission until a
separately approved, independently authenticated broker-source adapter exists.
Synthetic rows, replay, research outcomes and self-asserted ledger flags are not
proof of live executions. No orders or secrets are handled here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any


def _dt(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp_invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp_timezone_missing")
    return dt.astimezone(timezone.utc)


def _dec(value: Any, field: str, *, positive: bool = False) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(field + "_missing")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(field + "_invalid") from None
    if not d.is_finite() or (positive and d <= 0) or (not positive and d < 0):
        raise ValueError(field + "_invalid")
    return d


def _fail(reason: str) -> dict:
    return {
        "schema": "W6_RISK_LEDGER_RECON_V1",
        "status": "BLOCK",
        "portfolio_allowed": False,
        "ledger_verified": False,
        "ledger_complete": False,
        "reason": reason,
        "derived": None,
    }


def reconcile_for_review(snapshot: dict, *, now: datetime, max_age_seconds: int = 300) -> dict:
    """Derive verifiable arithmetic only, without asserting source trust.

    Input schema:
    - snapshot: captured_at (TZ-aware), trading_date (YYYY-MM-DD),
      account_equity, positions (complete open positions),
      closed_trades (complete ordered closed fills for session),
      positions_complete, closed_trades_complete, source.
    - each position: symbol, quantity, entry_price, stop_price, side=LONG.
    - each closed trade: trade_id, symbol, entry_time, exit_time,
      side=LONG, quantity, entry_price, exit_price, fees, tax, slippage,
      exit_reason (STOP_LOSS / OTHER), fill_id.
    This interface is *only a review schema*, not a production ledger adapter.
    """
    if not isinstance(snapshot, dict):
        return _fail("SNAPSHOT_MISSING")
    try:
        captured = _dt(snapshot.get("captured_at"))
        current = now.astimezone(timezone.utc) if now.tzinfo else None
        if current is None:
            return _fail("NOW_TIMEZONE_REQUIRED")
        if not (0 <= (current - captured).total_seconds() <= max_age_seconds):
            return _fail("SNAPSHOT_STALE_OR_FUTURE")
        if snapshot.get("positions_complete") is not True or snapshot.get("closed_trades_complete") is not True:
            return _fail("LEDGER_SCOPE_INCOMPLETE")
        if not str(snapshot.get("source") or "").strip():
            return _fail("SOURCE_UNSPECIFIED")
        equity = _dec(snapshot.get("account_equity"), "account_equity", positive=True)
        if not isinstance(snapshot.get("positions"), list) or not isinstance(snapshot.get("closed_trades"), list):
            return _fail("ROWS_NOT_LIST")
        date = str(snapshot.get("trading_date") or "")
        datetime.strptime(date, "%Y-%m-%d")
        pos_risk = Decimal("0")
        correlated_risk = None  # Requires independently approved sector/correlation mapping.
        used_symbols = set()
        for pos in snapshot["positions"]:
            if not isinstance(pos, dict) or pos.get("side") != "LONG":
                return _fail("POSITION_SIDE_UNSUPPORTED")
            sym = str(pos.get("symbol") or "")
            if not sym or sym in used_symbols:
                return _fail("POSITION_IDENTITY_DUPLICATE_OR_MISSING")
            used_symbols.add(sym)
            qty = _dec(pos.get("quantity"), "position_quantity", positive=True)
            entry = _dec(pos.get("entry_price"), "position_entry", positive=True)
            stop = _dec(pos.get("stop_price"), "position_stop", positive=True)
            if qty != qty.to_integral_value() or stop >= entry:
                return _fail("POSITION_STOP_OR_QUANTITY_INVALID")
            pos_risk += (entry - stop) * qty
        trades = []
        ids = set()
        fills = set()
        for row in snapshot["closed_trades"]:
            if not isinstance(row, dict) or row.get("side") != "LONG":
                return _fail("TRADE_SIDE_UNSUPPORTED")
            trade_id, fill_id = str(row.get("trade_id") or ""), str(row.get("fill_id") or "")
            if not trade_id or not fill_id or trade_id in ids or fill_id in fills:
                return _fail("TRADE_OR_FILL_ID_DUPLICATE")
            ids.add(trade_id)
            fills.add(fill_id)
            if not str(row.get("symbol") or ""):
                return _fail("TRADE_SYMBOL_MISSING")
            entry_dt, exit_dt = _dt(row.get("entry_time")), _dt(row.get("exit_time"))
            if entry_dt > exit_dt or exit_dt > captured:
                return _fail("TRADE_TIME_INVALID")
            if exit_dt.astimezone(timezone(timedelta(hours=8))).date().isoformat() != date:
                return _fail("TRADE_SESSION_MISMATCH")
            qty = _dec(row.get("quantity"), "trade_quantity", positive=True)
            if qty != qty.to_integral_value():
                return _fail("TRADE_QUANTITY_INVALID")
            entry = _dec(row.get("entry_price"), "trade_entry", positive=True)
            exit_price = _dec(row.get("exit_price"), "trade_exit", positive=True)
            costs = sum((_dec(row.get(k), k) for k in ("fees", "tax", "slippage")), Decimal(0))
            net = (exit_price - entry) * qty - costs
            reason = row.get("exit_reason")
            if reason not in ("STOP_LOSS", "OTHER"):
                return _fail("EXIT_REASON_MISSING_OR_UNRECOGNIZED")
            # A stop tag is not independently verified broker fill provenance.
            trades.append((exit_dt, trade_id, net, reason))
        # Same-timestamp fills cannot establish a unique ordering of stop events.
        trades.sort(key=lambda r: (r[0], r[1]))
        if len({x[0] for x in trades}) != len(trades):
            return _fail("TRADE_CLOSE_SEQUENCE_AMBIGUOUS")
        streak = 0
        for _, _, net, reason in trades:
            streak = streak + 1 if reason == "STOP_LOSS" and net < 0 else 0
        pnl = sum((r[2] for r in trades), Decimal(0))
        digest = sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
        return {
            "schema": "W6_RISK_LEDGER_RECON_V1",
            "status": "HOLD_UNVERIFIED_SOURCE",
            "portfolio_allowed": False,
            "ledger_verified": False,
            "ledger_complete": True,  # Claimed scope arithmetic checked; NOT broker verified.
            "reason": "SOURCE_ATTESTATION_AND_EXECUTION_RECONCILIATION_REQUIRED",
            "source_claim": snapshot["source"],
            "captured_at": snapshot["captured_at"],
            "input_sha256": digest,
            "derived": {
                "account_equity": float(equity),
                "daily_pnl": float(pnl),
                "open_risk": float(pos_risk),
                "concurrent_positions": len(used_symbols),
                "consecutive_stop_losses": streak,
                "correlated_open_risk": correlated_risk,
                "drawdown_pct": None,
                "closed_trades_count": len(trades),
            },
            "not_verified": [
                "broker_source_identity", "account_balance_reconciliation",
                "closed_trades_completeness", "positions_completeness",
                "stop_execution_causality", "correlation_exposure", "account_drawdown",
            ],
        }
    except (ValueError, TypeError, OverflowError) as exc:
        return _fail("INVALID_EVIDENCE:" + str(exc))
