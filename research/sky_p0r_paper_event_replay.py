"""Fail-closed PAPER_ONLY event-to-ledger adapter; no inferred fills or orders."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import math
from research.sky_paper_trade_trace import evaluate_paper_journal
from research.sky_p0r_order_gate import evaluate_paper_order
from src.cost_profiles import USER_CASH_DAYTRADE_20261022

def _at(value):
    if not isinstance(value, str):
        raise ValueError("TIMESTAMP_REQUIRED")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if t.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return t

def _num(value, *, positive=False):
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(value) or (positive and value <= 0)):
        raise ValueError("INVALID_NUMBER")
    return float(value)

def replay(events, *, run_id, scan_id, observed_at, source_artifact,
           simulator_version, starting_cash_twd=500000):
    """Replay externally captured simulator events, not scanner observations.

    Event stream allows ORDER, REJECT, FILL. A FILL needs a prior open order.
    Each completed trade needs explicit costs and timestamped fill evidence.
    """
    if not isinstance(events, list):
        raise ValueError("EVENTS_REQUIRED")
    if any(not isinstance(x, str) or not x for x in
           (run_id, scan_id, source_artifact, simulator_version)):
        raise ValueError("PROVENANCE_REQUIRED")
    observed = _at(observed_at)
    cash = _num(starting_cash_twd, positive=True)
    orders, positions, fills, rejections, seen = {}, {}, [], [], set()
    last = None
    stops = 0
    realized_net = 0.0
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("INVALID_EVENT")
        event_id, order_id = event.get("event_id"), event.get("order_id")
        if not isinstance(event_id, str) or not event_id or event_id in seen:
            raise ValueError("DUPLICATE_OR_MISSING_EVENT_ID")
        seen.add(event_id)
        if not isinstance(order_id, str) or not order_id:
            raise ValueError("ORDER_ID_REQUIRED")
        at = _at(event.get("event_time"))
        if (last and at < last) or at > observed or at.date() != observed.date():
            raise ValueError("NON_CAUSAL_EVENT")
        last = at
        if event.get("market_scan_id") != scan_id:
            raise ValueError("SCAN_ID_MISMATCH")
        kind = event.get("kind")
        if kind == "ORDER":
            if order_id in orders or event.get("side") not in ("BUY", "SELL"):
                raise ValueError("DUPLICATE_OR_INVALID_ORDER")
            symbol, signal = event.get("symbol"), event.get("signal_id")
            if not isinstance(symbol, str) or not symbol or not isinstance(signal, str) or not signal:
                raise ValueError("ORDER_PROVENANCE_REQUIRED")
            gate = (evaluate_paper_order(event, cash=cash,
                    equity=cash+sum(p["entry_price"]*p["shares"] for p in positions.values()),
                    positions=positions, realized_net=realized_net,
                    consecutive_stops=stops, observed_at=at.isoformat())
                    if event["side"] == "BUY" else None)
            deny = (event["side"] == "BUY" and (
                event.get("risk_status") != "ALLOW" or gate.get("status") != "ALLOW")) or (
                event["side"] == "SELL" and symbol not in positions)
            orders[order_id] = {"side": event["side"], "symbol": symbol,
                                "signal_id": signal, "status": "REJECTED" if deny else "OPEN",
                                "approved_shares": gate.get("recommended_shares", 0) if gate else None,
                                "candidate": event.get("candidate") if gate else None}
            if deny:
                rejections.append({"order_id": order_id, "reason": "RISK_OR_POSITION_BLOCKED"})
        elif kind == "REJECT":
            if order_id not in orders or orders[order_id]["status"] != "OPEN":
                raise ValueError("REJECTION_WITHOUT_ORDER")
            orders[order_id]["status"] = "REJECTED"
            rejections.append({"order_id": order_id, "reason": event.get("reason") or "REJECTED"})
        elif kind == "FILL":
            order = orders.get(order_id)
            if order is None or order["status"] != "OPEN":
                raise ValueError("FILL_WITHOUT_OPEN_ORDER")
            price, shares, fee = (_num(event.get("price"), positive=True),
                                  _num(event.get("shares"), positive=True),
                                  _num(event.get("fee_twd")))
            if fee < 0 or not shares.is_integer():
                raise ValueError("INVALID_FILL_QUANTITY_OR_COST")
            if event.get("fill_assumption") not in ("NEXT_BAR_OPEN_ESTIMATE", "LIMIT_TOUCH_ESTIMATE"):
                raise ValueError("FILL_ASSUMPTION_REQUIRED")
            symbol = order["symbol"]
            if order["side"] == "BUY":
                if symbol in positions:
                    raise ValueError("ADDS_NOT_SUPPORTED")
                stop = _num(event.get("original_stop"), positive=True)
                data_time = _at(event.get("market_data_time"))
                if stop >= price or data_time > at:
                    raise ValueError("INVALID_STOP_OR_FUTURE_DATA")
                plan = order.get("candidate")
                if (not isinstance(plan, dict) or price != plan.get("entry")
                    or stop != plan.get("stop") or shares > order["approved_shares"]):
                    raise ValueError("FILL_DIFFERS_FROM_CANONICAL_P0R_AUTHORIZATION")
                risk = (price - stop) * shares
                heat = sum((p["entry_price"]-p["original_stop"])*p["shares"]
                           for p in positions.values())
                if (price*shares > 100000 or risk > 5000 or heat+risk > 15000
                    or len(positions) >= 3 or cash < price*shares+fee or stops >= 2
                    or realized_net <= -10000):
                    raise ValueError("PAPER_RISK_CAPACITY_BLOCK")
                expected_fee = price * shares * USER_CASH_DAYTRADE_20261022.buy_commission_rate
                if abs(fee - expected_fee) > 0.1:
                    raise ValueError("BUY_FEE_PROFILE_MISMATCH")
                cash -= price*shares+fee
                positions[symbol] = {"symbol": symbol, "entry_price": price,
                    "original_stop": stop, "shares": int(shares), "entry_time": at.isoformat(),
                    "entry_fee_twd": fee, "market_data_time": data_time.isoformat(),
                    "fill_assumption": event["fill_assumption"], "signal_id": order["signal_id"]}
            else:
                p = positions.get(symbol)
                if p is None or p["shares"] != shares or _at(p["entry_time"]) >= at:
                    raise ValueError("UNMATCHED_OR_PARTIAL_EXIT")
                if event.get("reason") not in ("STOP", "TARGET", "MANUAL", "END_OF_DAY"):
                    raise ValueError("EXIT_REASON_REQUIRED")
                costs = {}
                for field in ("sale_tax_twd", "slippage_estimate_twd",
                              "spread_estimate_twd", "liquidity_impact_estimate_twd"):
                    costs[field] = _num(event.get(field))
                    if costs[field] < 0:
                        raise ValueError("NEGATIVE_EXECUTION_COST")
                profile = USER_CASH_DAYTRADE_20261022
                if (abs(fee - price*shares*profile.sell_commission_rate) > 0.1 or
                    abs(costs["sale_tax_twd"] - price*shares*profile.sell_tax_rate) > 0.1):
                    raise ValueError("SELL_COST_PROFILE_MISMATCH")
                row = {"paper_trade_id": event_id, "signal_id": p["signal_id"],
                    "market_scan_id": scan_id, "symbol": symbol,
                    "market_data_time": p["market_data_time"],
                    "entry_time": p["entry_time"], "exit_time": at.isoformat(),
                    "entry_price": p["entry_price"], "exit_price": price,
                    "shares": int(shares), "entry_fee_twd": p["entry_fee_twd"],
                    "exit_fee_twd": fee, "fill_assumption": p["fill_assumption"],
                    "source_type": "PAPER_SIMULATION", **costs}
                if not evaluate_paper_journal([row])["paper_cost_arithmetic_reconciled"]:
                    raise ValueError("INVALID_COST_JOURNAL")
                fills.append(row)
                single = evaluate_paper_journal([row])["paper_net_pnl_estimate_twd"]
                realized_net += single
                cash += price*shares-fee-sum(costs.values())
                stops = stops + 1 if event["reason"] == "STOP" else 0
                del positions[symbol]
            order["status"] = "FILLED"
        else:
            raise ValueError("UNSUPPORTED_EVENT_KIND")
    trace = evaluate_paper_journal(fills)
    pnl = trace["paper_net_pnl_estimate_twd"]
    if fills and pnl is None:
        raise ValueError("INCOMPLETE_JOURNAL")
    pnl = pnl if pnl is not None else 0.0
    if abs(pnl - realized_net) > 0.01:
        raise ValueError("PAPER_LEDGER_PNL_MISMATCH")
    open_risk = sum((p["entry_price"]-p["original_stop"])*p["shares"] for p in positions.values())
    snapshot = {"mode": "PAPER_ONLY", "run_id": run_id, "scan_id": scan_id,
        "observed_at": observed.isoformat(), "source_artifact": source_artifact,
        "simulator_version": simulator_version, "journal_scope": "FULL_DAY",
        "daily_realized_net_pnl_twd": round(pnl, 4), "consecutive_stops": stops,
        "open_positions": len(positions), "open_stop_risk_twd": round(open_risk, 4),
        "account_equity_twd": round(cash+sum(p["entry_price"]*p["shares"] for p in positions.values()), 4),
        "cash_twd": round(cash, 4),
        "positions": [{k: p[k] for k in ("symbol", "entry_price", "original_stop", "shares")}
                      for p in positions.values()],
        "open_order_count": sum(o["status"] == "OPEN" for o in orders.values()),
        "rejected_orders": rejections, "event_count": len(events),
        "event_source_independently_verified": False,
        "production_eligible": False, "live_trading_enabled": False}
    return snapshot, fills

def main():
    source = Path("output/sky_paper_runtime/events.json")
    if not source.exists():
        print(json.dumps({"verdict": "INSUFFICIENT_DATA", "reason": "SIMULATOR_EVENTS_MISSING"}))
        return 0
    # Never replay a retained events.json after a subsequent failed import.
    # A replay alone cannot prove its own origin: recheck current provenance
    # and reconstruct the event chain from the same independently bound input.
    from research.sky_p0r_market_event_producer import (
        produce, source_binding_verified, signal_import_status_verified,
    )
    base = source.parent
    evidence = Path("output/sky_p0r_paper_ledger_readback")
    def read_json(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    payload = read_json(source)
    market_input = read_json(base / "completed_market_evidence.json")
    binding = read_json(base / "source_binding.json")
    verified_bars = read_json(evidence / "verified_512_completed_bars.json")
    signal_status = read_json(evidence / "external_signal_source_status.json")
    market_status = read_json(evidence / "market_source_status.json")
    trusted = (
        isinstance(payload, dict) and isinstance(market_status, dict)
        and market_status.get("source_artifact_verified") is True
        and signal_import_status_verified(signal_status, binding)
        and source_binding_verified(market_input, binding, verified_bars)
    )
    if not trusted:
        print(json.dumps({"verdict": "INSUFFICIENT_DATA",
                          "reason": "CURRENT_PAPER_EVENT_SOURCE_UNVERIFIED",
                          "production_eligible": False}))
        return 0
    try:
        reconstructed = produce(market_input)
    except (ValueError, KeyError, TypeError):
        reconstructed = {}
    if (reconstructed.get("verdict") != "PAPER_EVENT_CHAIN_RECONCILED_ORIGIN_UNVERIFIED"
            or payload.get("events") != reconstructed.get("events")
            or payload.get("context") != {
                k: reconstructed["snapshot"][k] for k in (
                    "run_id", "scan_id", "observed_at",
                    "source_artifact", "simulator_version")
            }):
        print(json.dumps({"verdict": "INSUFFICIENT_DATA",
                          "reason": "PAPER_EVENT_CHAIN_REPLAY_MISMATCH",
                          "production_eligible": False}))
        return 0
    snapshot, fills = replay(payload["events"], **payload["context"])
    (source.parent / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (source.parent / "closed_fills.json").write_text(json.dumps(fills, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"verdict": "EVENT_REPLAY_ONLY_ORIGIN_UNVERIFIED", "event_count": len(payload["events"]),
                      "closed_fills": len(fills), "production_eligible": False}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
