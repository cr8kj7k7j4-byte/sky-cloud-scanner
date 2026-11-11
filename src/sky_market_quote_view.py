"""Read-only TSE/OTC quote viewer for a bounded explicit symbol selection.

This provides on-demand per-symbol evidence, NOT whole-market realtime coverage,
certified official TPEx realtime data, or executable signals.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .fugle import get_quote
from .official import load_official_universe
from .realtime_quote_evidence import fugle_executed_trade

TPE = ZoneInfo("Asia/Taipei")
SYMBOL = re.compile(r"^[1-9][0-9]{3,5}$")


def parse_symbols(value: str) -> list[str]:
    parts = [p.strip() for p in value.split(",")]
    if not parts or len(parts) > 20 or any(not SYMBOL.fullmatch(p) for p in parts):
        raise ValueError("Enter 1–20 comma-separated 4–6 digit symbols")
    return list(dict.fromkeys(parts))


def collect(symbols: list[str], *, now=None, universe=None, fetch=None) -> dict:
    now = now or datetime.now(TPE)
    fetch = fetch or get_quote
    report = {
        "schema": "SKY_MARKET_QUOTE_VIEW_V1",
        "requested_at_tpe": now.isoformat(),
        "source": "Fugle individual /intraday/quote, entitlement dependent",
        "scope": "SELECTED_SYMBOLS_ONLY_NOT_FULL_MARKET",
        "is_whole_market_realtime": False,
        "execution_authorized": False,
        "quotes": [],
    }
    if universe is None:
        try:
            universe, status = load_official_universe()
            report["universe_status"] = status
        except Exception as exc:
            universe = []
            report["universe_status"] = {"error_type": type(exc).__name__}
    by_code = {str(x["symbol"]): x for x in universe}
    for symbol in symbols:
        item = {"symbol": symbol, "exchange": None, "status": "UNKNOWN",
                "price": None, "trade_at_tpe": None, "action": "等待",
                "observed_price": None, "observed_at_tpe": None,
                "observed_price_requires_last_trade_time": False}
        meta = by_code.get(symbol)
        if not meta:
            item["status"] = "NOT_IN_VERIFIED_OFFICIAL_UNIVERSE"
            report["quotes"].append(item)
            continue
        item["exchange"] = meta.get("exchange")
        item["name"] = meta.get("name")
        try:
            payload = fetch(symbol)
            quote = payload.get("data", payload) if isinstance(payload, dict) else payload
            price, ts, status = fugle_executed_trade(quote, now=now)
            item["status"] = status
            item["price"] = price
            item["trade_at_tpe"] = ts.isoformat() if ts else None
            # Reference observation can be retained even if execution time is absent.
            # It must never be mistaken for a verified trade price.
            if isinstance(quote, dict) and quote.get("date") == now.date().isoformat() and quote.get("isTrial") is not True:
                trade = quote.get("lastTrade")
                trade = trade if isinstance(trade, dict) else {}
                raw_reference = quote.get("lastPrice")
                if raw_reference is None:
                    raw_reference = trade.get("price")
                try:
                    observed = float(raw_reference)
                except (ValueError, TypeError):
                    observed = 0.0
                if 0 < observed < float("inf"):
                    item["observed_price"] = observed
                    item["observed_at_tpe"] = now.isoformat()
        except PermissionError:
            item["status"] = "PLAN_RESTRICTED"
        except Exception as exc:
            item["status"] = "SOURCE_ERROR"
            item["error_type"] = type(exc).__name__
        report["quotes"].append(item)
    report["fresh_count"] = sum(x["status"] == "FRESH_EXECUTED_TRADE" for x in report["quotes"])
    report["observed_count"] = sum(x["observed_price"] is not None for x in report["quotes"])
    report["requested_count"] = len(symbols)
    report["all_selected_fresh"] = report["fresh_count"] == len(symbols)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True, help="comma separated codes; max 20")
    parser.add_argument("--out", default="output/market_quote_view/latest.json")
    args = parser.parse_args()
    symbols = parse_symbols(args.symbols)
    result = collect(symbols)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_selected_fresh"] and result["observed_count"] == 0:
        raise SystemExit("No usable same-day observations; see artifact, no trade")


if __name__ == "__main__":
    main()
