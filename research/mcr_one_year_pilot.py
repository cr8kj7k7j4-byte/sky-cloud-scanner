"""One-year MCR data audit and PRELIMINARY daily proxy replay.

No use of today's margins before publication; only previous-day end-of-day
data signal, next-session OPEN execution, fixed 5-session OPEN exit.
NOT the complete intraday MCR; does not infer margin calls or buy aggressors.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL = "https://api.finmindtrade.com/api/v4/data"
TZ = timezone(timedelta(hours=8))
# Frozen convenience pilot universe; NOT point-in-time whole market and not OOS.
SYMBOLS = ["1101", "1216", "1301", "1402", "2002", "2303", "2317", "2324",
           "2330", "2353", "2409", "2603", "2882", "2891", "3037", "3481",
           "3702", "4938", "5880", "8069"]
COSTS = (0.0045, 0.0065)
HOLDING_SESSIONS = 5


def fetch(dataset, symbol, start, end, token="", retries=2):
    params = {"dataset": dataset, "start_date": start, "end_date": end}
    if symbol:
        params["data_id"] = symbol
    url = URL + "?" + urlencode(params)
    headers = {"User-Agent": "SkyMCRResearch/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=25) as res:
                payload = json.load(res)
            if not isinstance(payload, dict):
                raise ValueError("non-object API reply")
            status = payload.get("status")
            rows = payload.get("data")
            if status != 200 or not isinstance(rows, list):
                return [], {"status": status, "msg": str(payload.get("msg"))[:140]}
            return rows, {"status": 200, "rows": len(rows)}
        except Exception as exc:
            if attempt == retries:
                return [], {"error": type(exc).__name__ + ": " + str(exc)[:120]}
            time.sleep(attempt + 1)


def finite(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def replay(price_rows, margin_rows, *, start, end):
    """Compare identical price trigger A against margin-confirmed B."""
    prices = {}
    balances = {}
    for row in price_rows:
        d = str(row.get("date", ""))
        o, c = finite(row.get("open")), finite(row.get("close"))
        if o is not None and c is not None and o > 0 and c > 0:
            prices[d] = (o, c)
    for row in margin_rows:
        d = str(row.get("date", ""))
        b = finite(row.get("MarginPurchaseTodayBalance"))
        if b is not None and b >= 0:
            balances[d] = b
    days = sorted(prices)
    trades = {"A_PRICE_ONLY": [], "B_PRICE_PLUS_DELEVERAGING": []}
    for i in range(6, len(days) - HOLDING_SESSIONS - 1):
        day = days[i]
        if not (start <= day <= end):
            continue
        # Signal uses CURRENT CLOSE and previously published margin balance.
        # No same-day margin, since release typically post close.
        previous_day = days[i - 1]
        older_day = days[i - 2]
        previous_5day = days[i - 5]
        pclose = prices[previous_day][1]
        close = prices[day][1]
        ref = prices[previous_5day][1]
        if pclose <= 0 or ref <= 0:
            continue
        signal = close / pclose - 1 <= -0.05 and close / ref - 1 <= -0.10
        if not signal:
            continue
        entry_day = days[i+1]
        exit_day = days[i+1+HOLDING_SESSIONS]
        entry = prices[entry_day][0]
        exit_ = prices[exit_day][0]
        if entry <= 0:
            continue
        gross = exit_ / entry - 1
        record = {"signal_date": day, "entry_date": entry_day,
                  "exit_date": exit_day, "gross_return": gross,
                  "trade_margin_available": previous_day in balances and older_day in balances}
        trades["A_PRICE_ONLY"].append(record)
        # Previous-day margin value is conservative; no publication timestamp
        # in raw FinMind EOD dataset. This still requires provenance validation.
        if previous_day in balances and older_day in balances and balances[older_day] > 0:
            if balances[previous_day] < balances[older_day]:
                trades["B_PRICE_PLUS_DELEVERAGING"].append(record)
    return trades, len(prices), len(balances)


def metrics(trades, cost):
    values = [t["gross_return"] - cost for t in trades]
    n = len(values)
    wins = sum(v for v in values if v > 0)
    losses = sum(-v for v in values if v < 0)
    equity = 0
    peak = 0
    drawdown = 0
    for v in sorted(zip((t["exit_date"] for t in trades), values)):
        equity += v[1]
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return {
        "n": n,
        "mean_net_return_pct": round(100 * sum(values) / n, 4) if n else None,
        "win_rate_pct": round(100 * sum(v > 0 for v in values) / n, 2) if n else None,
        "profit_factor": round(wins / losses, 4) if losses else None,
        "sum_of_trade_returns_drawdown_pct": round(100 * drawdown, 4) if n else None,
        "note": "Single-trade sequential drawdown proxy, NOT portfolio max drawdown.",
    }


def run(start, end, symbols, token):
    report = {
        "model": "Sky MCR V1.5", "report_type": "PILOT_DAILY_PROXY_NOT_FULL_MCR",
        "research_window": [start, end], "symbol_selection": "fixed 20-symbol convenience pilot; not full-market PIT",
        "data_retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "execution": "signal at close; next trading day open; exit after 5 additional sessions at open",
        "no_intraday_orderflow": True, "estimated_margin_maintenance_verified": False,
        "financing_margin_call_verified": False, "production_signal": False,
        "thresholds_fixed": {"daily_loss": -0.05, "five_day_loss": -0.10, "margin_balance_change": "<0"},
        "costs": list(COSTS), "per_symbol": {},
        "dataset_access_probe": {},
    }
    # Source contract: the true maintenance series requires Sponsor access.
    # Fetch ONLY one symbol to assess entitlement rather than assume access.
    mr, mstatus = fetch("TaiwanStockMarginMaintenance", symbols[0], start, end, token)
    report["dataset_access_probe"] = {"dataset": "TaiwanStockMarginMaintenance",
                                      "response": mstatus, "rows": len(mr),
                                      "is_model_usable": False,
                                      "reason": "Requires separately verified vendor estimate definition, entitlement and PIT publish time"}
    merged = {"A_PRICE_ONLY": [], "B_PRICE_PLUS_DELEVERAGING": []}
    for j, symbol in enumerate(symbols):
        p, ps = fetch("TaiwanStockPrice", symbol, start, end, token)
        m, ms = fetch("TaiwanStockMarginPurchaseShortSale", symbol, start, end, token)
        out, nprice, nmargin = replay(p, m, start=start, end=end)
        report["per_symbol"][symbol] = {"price_api": ps, "margin_api": ms,
                                         "daily_price_rows_valid": nprice,
                                         "daily_financing_rows_valid": nmargin,
                                         "A_events": len(out["A_PRICE_ONLY"]),
                                         "B_events": len(out["B_PRICE_PLUS_DELEVERAGING"])}
        for family in merged:
            merged[family].extend({**t, "symbol": symbol} for t in out[family])
        if j != len(symbols) - 1:
            time.sleep(0.20)
    report["comparisons"] = {name: {str(cost): metrics(trades,cost) for cost in COSTS}
                             for name,trades in merged.items()}
    report["evaluated_event_sessions"] = {name: len(set(t["signal_date"] for t in ts))
                                          for name,ts in merged.items()}
    report["data_quality"] = {
        "symbols_requested": len(symbols),
        "price_symbols_with_rows": sum(x["daily_price_rows_valid"] > 0 for x in report["per_symbol"].values()),
        "margin_symbols_with_rows": sum(x["daily_financing_rows_valid"] > 0 for x in report["per_symbol"].values())
    }
    report["decision"] = "INSUFFICIENT_DATA"
    report["gates"] = {
        "complete_MCR_intraday_flow": False, "full_universe_PIT": False,
        "genuine_future_OOS": False, "200_independent_eligible_events": False,
        "20_future_trading_days": False, "two_market_regimes": False,
        "execution_realism": False,
    }
    report["why_not_positive_certification"] = [
        "No reliable 1y point-in-time full-universe estimated maintenance + intraday order flow",
        "Daily proxy A/B cannot test seller exhaustion, aggressor buy, stop/target sequencing",
        "Convenience symbols and history already researched are not fresh independent OOS",
        "No real bid-ask fill, short borrowability or broker-specific observed costs",
        "Event overlap, sector clustering and portfolio heat not yet fully replayed",
    ]
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2025-11-10")
    p.add_argument("--end", default="2026-11-06")
    p.add_argument("--out", default="research_output/mcr_one_year_pilot.json")
    p.add_argument("--symbols", default=",".join(SYMBOLS))
    args = p.parse_args()
    out = run(args.start, args.end, args.symbols.split(","), os.getenv("FINMIND_API_TOKEN", ""))
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"decision": out["decision"], "data_quality": out["data_quality"],
                      "comparisons": out["comparisons"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
