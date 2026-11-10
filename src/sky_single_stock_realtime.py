"""Fail-closed single-stock Fugle API realtime evidence collector.

Read-only data collection. Does NOT produce trade triggers, scores, orders or risk sizing.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import fugle

TPE = timezone(timedelta(hours=8))


def timestamp_tpe(value):
    """Accept Fugle epoch microseconds/milliseconds/seconds; return ISO TPE."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        if number > 1e14:
            number /= 1_000_000
        elif number > 1e11:
            number /= 1_000
        return datetime.fromtimestamp(number, TPE).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def collect(symbol: str, now=None) -> dict:
    now = now or datetime.now(TPE)
    if not (symbol.isdigit() and 4 <= len(symbol) <= 6):
        return {"status": "INVALID_SYMBOL", "symbol": symbol, "action": "禁止交易"}
    result = {
        "symbol": symbol, "source": "Fugle MarketData API /intraday/quote",
        "requested_at_tpe": now.isoformat(), "action": "等待",
        "execution_authorized": False, "live_order_enabled": False,
        "scores": None, "entry_trigger": None, "max_entry": None,
        "stop": None, "targets": None, "net_rr": None,
    }
    try:
        quote = fugle.get_quote(symbol)
        ticker = fugle.get_ticker(symbol)
        if not isinstance(quote, dict) or not isinstance(ticker, dict):
            raise ValueError("Invalid Fugle response payload")
        trade = quote.get("lastTrade")
        trade = trade if isinstance(trade, dict) else {}
        last_price = trade.get("price") if trade.get("price") is not None else quote.get("lastPrice")
        # A quote refresh/closeTime is not a last executed-trade timestamp.
        last_time = timestamp_tpe(trade.get("time"))
        updated_time = timestamp_tpe(quote.get("lastUpdated"))
        result.update({
            "quote_date": quote.get("date"), "last_price": last_price,
            "observed_price": last_price, "observed_at_tpe": now.isoformat(),
            "observation_requires_last_trade_time": False,
            "executed_trade_verified": False,
            "last_trade_tpe": last_time, "last_updated_tpe": updated_time,
            "high": quote.get("highPrice"), "low": quote.get("lowPrice"),
            "open": quote.get("openPrice"), "average_price": quote.get("avgPrice"),
            "volume": (quote.get("total") or {}).get("tradeVolume"),
            "best_bid": ((quote.get("bids") or [{}])[0]).get("price"),
            "best_ask": ((quote.get("asks") or [{}])[0]).get("price"),
            "day_trade_eligible": ticker.get("canDayTrade"),
            "is_disposition": ticker.get("isDisposition"),
            "quote_market": quote.get("market"),
        })
        if (isinstance(last_price, bool) or not isinstance(last_price, (float, int))
                or last_price <= 0):
            result["status"] = "INVALID_OR_MISSING_PRICE"
        elif quote.get("date") != now.date().isoformat():
            result["status"] = "STALE_TRADING_DATE"
        elif not last_time:
            # Preserve an observed price while withholding verified-live status.
            result["status"] = "UNVERIFIED_EXECUTION_TIME"
        else:
            seen = datetime.fromisoformat(last_time)
            quote_date = quote.get("date")
            age = (now - seen).total_seconds()
            result["quote_age_seconds"] = round(age, 1)
            if quote_date != now.date().isoformat() or seen.date() != now.date():
                result["status"] = "STALE_TRADING_DATE"
            elif age < -30:
                result["status"] = "FUTURE_QUOTE_TIMESTAMP"
            elif age > 120:
                result["status"] = "STALE_QUOTE"
            elif ticker.get("canDayTrade") is not True:
                result["status"] = "DAY_TRADE_NOT_ELIGIBLE"
            elif ticker.get("isDisposition") is True:
                result["status"] = "DISPOSITION_NO_NEW_ENTRY"
            elif last_price >= float(os.environ.get("MAX_PRICE", "100")):
                result["status"] = "PRICE_CAP_EXCEEDED"
            else:
                result["status"] = "REALTIME_QUOTE_VERIFIED"
                result["executed_trade_verified"] = True
        return result
    except Exception as exc:
        result.update({"status": "QUOTE_FETCH_FAILED", "error_type": type(exc).__name__})
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    payload = collect(args.symbol)
    path = Path(args.output or f"output/single_stock/{args.symbol}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["status"] != "REALTIME_QUOTE_VERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
