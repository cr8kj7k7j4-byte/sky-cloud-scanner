"""Canonical P0-R/P0-X PAPER_ONLY order verification. No order placement."""
from __future__ import annotations
from src.cost_profiles import USER_CASH_DAYTRADE_20261022
from src.risk_engine import evaluate_candidate


def evaluate_paper_order(order, *, cash, equity, positions, realized_net,
                         consecutive_stops, observed_at):
    """Re-evaluate existing paper-ledger counters and costs; never trust caller ALLOW."""
    if not isinstance(order, dict):
        return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
    plan = order.get("candidate")
    costs = order.get("execution_assumptions")
    if not isinstance(plan, dict) or not isinstance(costs, dict):
        return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
    required = ("entry_slippage_bps", "exit_slippage_bps", "spread_bps",
                "liquidity_penalty_bps", "fill_probability")
    if any(costs.get(field) is None or isinstance(costs[field], bool) for field in required):
        return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
    try:
        from math import isfinite
        if any(not isfinite(float(costs[field])) or float(costs[field]) < 0
               for field in required[:4]):
            return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
        if not 0 < float(costs["fill_probability"]) <= 1:
            return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
        policy = USER_CASH_DAYTRADE_20261022.to_execution_policy(
            **{field: float(costs[field]) for field in required},
            enforce_gate=True, min_execution_rr=1.5)
        open_risk = sum((p["entry_price"] - p["original_stop"]) * p["shares"]
                        for p in positions.values())
        ledger = {"mode": "PAPER_ONLY", "daily_realized_net_pnl_twd": realized_net,
                  "consecutive_stops": consecutive_stops,
                  "open_positions": len(positions), "open_stop_risk_twd": open_risk}
        context = {"mode": "PAPER_ONLY", "account_equity": equity,
                   "daily_pnl": realized_net, "consecutive_losses": consecutive_stops,
                   "concurrent_positions": len(positions), "open_risk": open_risk,
                   "paper_ledger": ledger, "execution_policy": policy}
        result = evaluate_candidate(plan, context)
    except (ValueError, TypeError, OverflowError, ZeroDivisionError):
        return {"status": "RISK_INPUT_REQUIRED", "recommended_shares": 0}
    if result.get("status") != "ALLOW":
        return {"status": result.get("status"), "recommended_shares": 0}
    return result
