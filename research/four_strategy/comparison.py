"""Research-only matched trade diagnostics; NOT a portfolio simulator.

Never describe these diagnostics as a validated backtest, real fill, or
strategy ranking. No entry signal is generated. Missing evidence fails closed.
"""
from collections import Counter
from datetime import datetime
from math import isfinite

from research_gate import validate_signal

PRIMARY_COST = 0.0045
STRESS_COST = 0.0065


def _time(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    return value


def _finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("invalid_" + field)
    return float(value)


def evaluate_trades(trades, cost_rate=PRIMARY_COST):
    """Diagnostic single-trade R metrics for strictly simulated fills.

    Input signals follow research_gate; additional fields:
    exit_price, exit_at, execution_evidence="SIMULATED", and outcome_source.
    Cost is modeled as a fraction of entry notional (round-trip proxy).
    This does NOT prove executable fills, 3-position portfolio validity,
    borrowability, or independent OOS samples.
    """
    cost_rate = _finite_number(cost_rate, "cost_rate")
    if not 0 <= cost_rate < 1:
        raise ValueError("invalid_cost_rate")
    if not isinstance(trades, (list, tuple)) or not trades:
        raise ValueError("missing_trades")
    used = set()
    seen_strategy = set()
    output = []
    for trade in trades:
        validate_signal(trade, used)
        if trade.get("execution_evidence") != "SIMULATED":
            raise ValueError("simulation_only")
        if not isinstance(trade.get("outcome_source"), str) or not trade["outcome_source"].strip():
            raise ValueError("missing_outcome_source")
        if "exit_at" not in trade:
            raise ValueError("missing_exit_at")
        if _time(trade["exit_at"]) <= _time(trade["decision_at"]):
            raise ValueError("noncausal_exit")
        if "exit_price" not in trade:
            raise ValueError("missing_exit_price")
        exit_price = _finite_number(trade["exit_price"], "exit_price")
        if exit_price <= 0:
            raise ValueError("invalid_exit_price")
        symbol = trade["symbol"]
        risk_per_share = float(trade["entry_price"]) - float(trade["stop_price"])
        if risk_per_share <= 0:
            raise ValueError("invalid_risk_denominator")
        gross_r = (exit_price - trade["entry_price"]) / risk_per_share
        net_r = (exit_price - trade["entry_price"] -
                 float(trade["entry_price"]) * cost_rate) / risk_per_share
        output.append({"id": trade["decision_id"], "strategy": trade["strategy_id"],
                       "symbol": symbol, "decision_at": _time(trade["decision_at"]),
                       "gross_r": gross_r, "net_r": net_r})
        seen_strategy.add(trade["strategy_id"])
    # This function is intentionally per-trade. Shared-capital position overlap,
    # execution feasibility and max portfolio drawdown remain unverified.
    results = {}
    for strategy in sorted(seen_strategy):
        sample = sorted((x for x in output if x["strategy"] == strategy),
                        key=lambda x: (x["decision_at"], x["id"]))
        values = [x["net_r"] for x in sample]
        total_win = sum(v for v in values if v > 0)
        total_loss = -sum(v for v in values if v < 0)
        count = Counter(x["symbol"] for x in sample)
        results[strategy] = {
            "sample_count": len(sample),
            "net_expectancy_r": sum(values) / len(values),
            "profit_factor": total_win / total_loss if total_loss > 0 else None,
            "win_rate": sum(v > 0 for v in values) / len(values),
            "max_symbol_fraction": max(count.values()) / len(sample),
            "all_net_r": values,
            "cost_rate": cost_rate,
            "portfolio_max_drawdown": None,
            "portfolio_validated": False,
            "historical_oos_validated": False,
            "status": "INSUFFICIENT_DATA",
        }
    return results


def compare_cost_stress(trades):
    return {"primary": evaluate_trades(trades, PRIMARY_COST),
            "stress": evaluate_trades(trades, STRESS_COST)}
