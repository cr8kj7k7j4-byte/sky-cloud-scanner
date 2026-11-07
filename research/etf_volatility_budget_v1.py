"""Frozen V1 pilot: 0050 cash/ETF unlevered monthly volatility budget.
Research-only, one year, excludes dividends/split audit; no trading signals.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

START = "2025-11-10"
END = "2026-11-06"
WARMUP = "2025-08-01"
SYMBOL = "0050"
VOL_LOOKBACK = 20
TARGET_ANNUAL_VOL = 0.20
COSTS = (0.0045, 0.0065)


def load_data(token=""):
    params = urlencode({"dataset": "TaiwanStockPrice", "data_id": SYMBOL,
                       "start_date": WARMUP, "end_date": END})
    headers = {"User-Agent": "SkyVolatilityBudgetResearch/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request("https://api.finmindtrade.com/api/v4/data?" + params,
                             headers=headers), timeout=40) as response:
            payload = json.load(response)
        if payload.get("status") != 200 or not isinstance(payload.get("data"), list):
            return [], {"error": str(payload.get("msg", "API_RESPONSE"))[:150]}
        rows = {}
        for row in payload["data"]:
            try:
                d, o, c = str(row["date"]), float(row["open"]), float(row["close"])
                if o > 0 and c > 0 and math.isfinite(o) and math.isfinite(c):
                    rows[d] = (d, o, c)
            except (ValueError, KeyError, TypeError):
                continue
        return sorted(rows.values()), {"status": 200, "rows": len(rows)}
    except Exception as exc:
        return [], {"error": type(exc).__name__ + ": " + str(exc)[:140]}


def target_weight(data, trade_index):
    """Signal calculated from closes strictly BEFORE trade session."""
    prices = [row[2] for row in data]
    end = trade_index - 1
    if end < VOL_LOOKBACK:
        return 0.0
    trailing = prices[end - VOL_LOOKBACK:end + 1]
    returns = [math.log(trailing[i] / trailing[i-1])
               for i in range(1, len(trailing))]
    realized_vol = statistics.stdev(returns) * math.sqrt(252)
    if not math.isfinite(realized_vol) or realized_vol <= 0:
        return 0.0
    return min(1.0, TARGET_ANNUAL_VOL / realized_vol)


def simulate(data, cost, strategy):
    """Unlevered fractionally sized hypothetical sleeve, monthly-open trades."""
    cash, shares = 1.0, 0.0
    observations, transactions = [], []
    previous_month = None
    for i, (d, op, cl) in enumerate(data):
        if d < START:
            continue
        current_month = d[:7]
        rebalance = current_month != previous_month
        previous_month = current_month
        if rebalance:
            weight = target_weight(data, i) if strategy == "VOL_BUDGET" else 1.0
            before = cash + shares * op
            target_shares = before * weight / op
            difference = target_shares - shares
            half = cost / 2
            if difference > 0:
                affordable = cash / (op * (1 + half))
                qty = min(difference, affordable)
                if qty > 1e-12:
                    cash -= qty * op * (1 + half)
                    shares += qty
                    transactions.append((d, "BUY", qty, op))
            elif difference < 0:
                qty = min(-difference, shares)
                cash += qty * op * (1 - half)
                shares -= qty
                transactions.append((d, "SELL", qty, op))
        observations.append((d, cash + shares * cl, shares > 1e-10))
    if not observations:
        return {"n_days": 0}
    # Comparable, hypothetical end-of-window liquidation (never implied filled).
    final_close = data[-1][2]
    final_nav = cash + shares * final_close * (1 - cost / 2)
    running_peak, max_dd = 1.0, 0.0
    for _, nav, _ in observations:
        running_peak = max(running_peak, nav)
        max_dd = min(max_dd, nav / running_peak - 1)
    return {
        "n_days": len(observations),
        "total_net_return_pct": round((final_nav - 1) * 100, 4),
        "mark_to_market_max_drawdown_pct": round(max_dd * 100, 4),
        "trade_actions": len(transactions),
        "invested_days": sum(x[2] for x in observations),
        "final_position_marked_for_liquidation": shares > 0,
        "latest_close_date": observations[-1][0],
    }


def run(token):
    rows, api = load_data(token)
    result = {
        "model": "ETF_VOLATILITY_BUDGET_RESEARCH_V1",
        "state": "INSUFFICIENT_DATA",
        "production_signal": False,
        "symbol": SYMBOL,
        "period": [START, END],
        "api": api,
        "valid_price_rows": len(rows),
        "fixed_rules": {"volatility_lookback_sessions": 20, "target_annual_vol": 0.20,
                        "rebalance": "first open of each calendar month",
                        "execution": "previous session information only; unlevered; cash or ETF"},
        "results": {},
        "limitations": [
            "Historical raw OHLC not dividend-adjusted or audited for corporate actions",
            "One ETF / one year cannot establish stable expectation or independent OOS",
            "No real spread/slippage and no order fill, no broker quantity limits",
            "Portfolio 1R, 100k position cap and live positions not simulated",
            "No strategy promotion or trading authority"
        ],
    }
    if len(rows) >= 60:
        for cost in COSTS:
            result["results"][str(cost)] = {
                "VOL_BUDGET": simulate(rows, cost, "VOL_BUDGET"),
                "BUY_HOLD": simulate(rows, cost, "BUY_HOLD")
            }
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="research_output/volatility_budget_pilot.json")
    args = p.parse_args()
    result = run(os.getenv("FINMIND_API_TOKEN", ""))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"state": result["state"], "valid_price_rows": result["valid_price_rows"],
                      "api": result["api"], "results": result["results"]}, ensure_ascii=False))
