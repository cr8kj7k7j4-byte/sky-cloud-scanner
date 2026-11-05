"""Sky Bidirectional Alpha V1: isolated, research-only, fail-closed live observer.

This is NOT a validated trading strategy. It never emits executable entries.
Official TWSE/TPEx universe + operational MIS quotes; OTC MIS is not TPEx
official certified real-time. No live short-borrow availability is assumed.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
RESEARCH_VERSION = "SKY_BIDIRECTIONAL_ALPHA_V1_RESEARCH"
MIN_COVERAGE = 80.0
MAX_PRICE = 100.0
MIN_TURNOVER = 10_000_000

def _num(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError, OverflowError):
        return None

def classify_observations(rows, *, current_session: bool, coverage_ok: bool):
    """Directional watchlists are NOT validated signals or tradable advice."""
    long_watch, short_watch = [], []
    for row in rows:
        p = _num(row.get("price") or row.get("last") or row.get("close"))
        change = _num(row.get("change_pct"))
        turnover = _num(row.get("trade_value") or row.get("turnover"))
        if p is None or change is None or not (0 < p < MAX_PRICE):
            continue
        if turnover is None or turnover < MIN_TURNOVER:
            continue
        if not current_session or not coverage_ok:
            continue
        observation = {
            "symbol": str(row.get("symbol", "")),
            "exchange": row.get("exchange"),
            "observed_price": p,
            "observed_change_pct": change,
            "turnover": turnover,
            "long_score": None,
            "short_score": None,
            "entry_trigger": None,
            "max_acceptable_price": None,
            "stop": None,
            "target_1": None,
            "target_2": None,
            "net_rr": None,
            "classification": "RESEARCH_WATCH_ONLY",
            "action": "觀察",
            "no_trade_reason": "Missing audited 1m/order-flow, execution quality, cost and eligible-short evidence",
        }
        if change > 0:
            long_watch.append(observation)
        elif change < 0:
            short_watch.append(observation)
    long_watch.sort(key=lambda d: d["observed_change_pct"], reverse=True)
    short_watch.sort(key=lambda d: d["observed_change_pct"])
    return long_watch[:20], short_watch[:20]

def run(now=None):
    from src.official import load_official_universe, fetch_mis_quotes
    from src.realtime_quote_evidence import validate_whole_market_rows

    now = now or datetime.now(TZ)
    report = {
        "schema": RESEARCH_VERSION, "generated_at_taipei": now.isoformat(),
        "mode": "RESEARCH_ONLY", "production_modified": False,
        "order_execution_enabled": False, "short_trading_authorized": False,
        "status": "BLOCKED_NO_TRADE", "action": "禁止交易",
        "universe_count": 0, "valid_quote_count": 0,
        "quote_coverage_pct": 0, "long_watch": [], "short_watch": [],
        "risks": [
            "No backtested positive expectancy; all signals research-only",
            "Short selling eligibility and same-day borrow/recall not verified",
            "OTC via TWSE MIS is an operational fallback, not TPEx certified realtime",
            "Spread/slippage/fill/short recall and full execution cost not verified",
            "Do not trade or automatically place orders from this report",
        ],
    }
    # Deliberate hard stop pre-open, weekends or outside continuous session.
    session = now.weekday() < 5 and time(9, 0) <= now.time() <= time(13, 30)
    report["regular_session"] = session
    if not session:
        report["reason"] = "OUTSIDE_REGULAR_TAIWAN_STOCK_SESSION"
        return report
    try:
        universe, source_status = load_official_universe()
        report["universe_count"] = len(universe)
        report["universe_source_health"] = source_status
        rows, warnings = fetch_mis_quotes(universe)
        audit = validate_whole_market_rows(
            universe, rows, now=now,
            min_coverage_pct=MIN_COVERAGE, min_exchange_pct=70.0,
        )
        report["quote_coverage_pct"] = audit.get("quote_coverage_pct", 0)
        report["valid_quote_count"] = audit.get("valid_quote_count", 0)
        report["warnings"] = warnings
        report["market_data_gate"] = (
            "PASS_OPERATIONAL_ONLY" if audit.get("valid_whole_market_operational")
            else "BLOCKED_EXTERNAL_DATA"
        )
        report["source_scope"] = "TWSE MIS TSE/OTC operational; OTC not TPEx certified realtime"
        long_watch, short_watch = classify_observations(
            audit.get("accepted_rows", []),
            current_session=session,
            coverage_ok=bool(audit.get("valid_whole_market_operational")),
        )
        report["long_watch"], report["short_watch"] = long_watch, short_watch
        report["reason"] = (
            "RESEARCH_WATCHLIST_ONLY_NO_TRADE"
            if audit.get("valid_whole_market_operational")
            else "CURRENT_SESSION_WHOLE_MARKET_COVERAGE_INSUFFICIENT"
        )
    except Exception as exc:
        report["reason"] = "DATA_SOURCE_OR_RUNTIME_FAILURE"
        report["error_class"] = type(exc).__name__
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/bidirectional/latest.json")
    args = parser.parse_args()
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "reason": report.get("reason"),
        "data_gate": report.get("market_data_gate"),
        "long_watch_count": len(report["long_watch"]),
        "short_watch_count": len(report["short_watch"]),
        "report": str(p),
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
