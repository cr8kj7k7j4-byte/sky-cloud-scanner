"""Bounded live Fugle entitlement/rate evidence and two-stage research check.

Does not establish contracted API limits, certify whole market executed trades,
or authorize orders. Never print raw errors/keys or expose private payloads.
"""
import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from src.fugle import snapshot_quotes, get_quote
from src.realtime_quote_evidence import fugle_executed_trade

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/fugle_two_stage_acceptance.json")
MAX_QUOTE_CALLS = 8
MIN_INTERVAL_SECONDS = 1.2


def http_status(exc):
    resp = getattr(exc, "response", None)
    return getattr(resp, "status_code", None)


def error_category(exc):
    status = http_status(exc)
    if status == 429:
        return "RATE_LIMIT_429"
    if status in (401, 403):
        return "AUTH_OR_PLAN_DENIED"
    if isinstance(exc, requests.Timeout):
        return "TIMEOUT"
    if status is not None:
        return "HTTP_ERROR_" + str(status)
    return "REQUEST_ERROR_" + type(exc).__name__


def snapshot_audit(fetch=snapshot_quotes, checked=None):
    checked = checked or datetime.now(TZ)
    reports = {}
    raw = {}
    for market in ("TSE", "OTC"):
        try:
            payload = fetch(market)
            rows = payload.get("data") if isinstance(payload, dict) else None
            valid_shape = isinstance(rows, list)
            reports[market] = {
                "endpoint": "/snapshot/quotes/" + market,
                "request_status": "OK" if valid_shape else "INVALID_SHAPE",
                "provider_date": payload.get("date") if isinstance(payload, dict) else None,
                "returned_rows": len(rows) if valid_shape else 0,
                "same_date": (payload.get("date") == checked.date().isoformat()) if isinstance(payload, dict) else False,
                "has_per_symbol_execution_time": (sum(
                    isinstance(q, dict) and isinstance(q.get("lastTrade"), dict)
                    and q["lastTrade"].get("time") is not None for q in rows
                ) if valid_shape else 0),
            }
            raw[market] = payload if valid_shape else {}
        except Exception as exc:
            reports[market] = {"endpoint": "/snapshot/quotes/" + market,
                               "request_status": error_category(exc),
                               "returned_rows": 0, "same_date": False}
            raw[market] = {}
            if http_status(exc) == 429:
                break
    return reports, raw


def choose_samples(raw, max_calls=MAX_QUOTE_CALLS):
    """Alternate TSE/OTC, select valid reference-priced stocks below TWD100."""
    pools = {}
    for market in ("TSE", "OTC"):
        rows = raw.get(market, {}).get("data", [])
        pool = []
        for q in rows:
            if not isinstance(q, dict) or q.get("isTrial") is True:
                continue
            symbol = str(q.get("symbol") or "")
            try:
                price = float(q.get("lastPrice") or (q.get("lastTrade") or {}).get("price"))
                volume = float(q.get("tradeVolume") or 0)
            except (TypeError, ValueError):
                continue
            if symbol.isdigit() and 4 <= len(symbol) <= 6 and 0 < price < 100 and volume > 0:
                pool.append((symbol, price, volume))
        pools[market] = sorted(pool, key=lambda x: x[2], reverse=True)
    selected = []
    for i in range(max_calls):
        market = "TSE" if i % 2 == 0 else "OTC"
        if pools[market]:
            selected.append((market, pools[market].pop(0)[0]))
        elif pools["OTC" if market == "TSE" else "TSE"]:
            other = "OTC" if market == "TSE" else "TSE"
            selected.append((other, pools[other].pop(0)[0]))
        else:
            break
    return selected


def audit_individual(raw, fetch=get_quote, checked=None, sleep=time.sleep,
                     interval=MIN_INTERVAL_SECONDS, max_calls=MAX_QUOTE_CALLS):
    checked = checked or datetime.now(TZ)
    selected = choose_samples(raw, min(max_calls, MAX_QUOTE_CALLS))
    items = []
    errors = Counter()
    for i, (market, symbol) in enumerate(selected):
        if i:
            sleep(interval)
        entry = {"market": market, "symbol": symbol, "status": "NOT_VERIFIED",
                 "has_last_trade_time": False, "fresh_executed": False}
        try:
            payload = fetch(symbol)
            q = payload.get("data", payload) if isinstance(payload, dict) else {}
            if not isinstance(q, dict) or str(q.get("symbol") or "") != symbol:
                entry["status"] = "SYMBOL_MISMATCH_OR_BAD_PAYLOAD"
            elif str(q.get("market") or "").upper() not in (
                ("TSE", "TWSE") if market == "TSE" else ("OTC", "TPEX")
            ):
                entry["status"] = "MARKET_MISMATCH"
            else:
                trade = q.get("lastTrade") if isinstance(q.get("lastTrade"), dict) else {}
                entry["has_last_trade_time"] = trade.get("time") is not None
                if trade.get("price") is None or trade.get("time") is None:
                    entry["status"] = "NO_LAST_TRADE_EVIDENCE"
                else:
                    price, executed, status = fugle_executed_trade(q, now=checked)
                    entry["status"] = status
                    entry["fresh_executed"] = status == "FRESH_EXECUTED_TRADE"
                    entry["last_trade_time"] = executed.isoformat() if executed else None
                    entry["verified_price"] = price if entry["fresh_executed"] else None
        except Exception as exc:
            entry["status"] = error_category(exc)
            errors[entry["status"]] += 1
        items.append(entry)
        if entry["status"] == "RATE_LIMIT_429":
            break  # stop immediately; do not test provider throttling by flooding
    return {"requested_limit": min(max_calls, MAX_QUOTE_CALLS),
            "requests_made": len(items),
            "fresh_executed": sum(i["fresh_executed"] for i in items),
            "status_counts": dict(Counter(i["status"] for i in items)),
            "any_429": any(i["status"] == "RATE_LIMIT_429" for i in items),
            "items": items}


def main():
    checked = datetime.now(TZ)
    snapshot, raw = snapshot_audit(checked=checked)
    individual = audit_individual(raw, checked=datetime.now(TZ))
    snapshot_rate_limited = any(
        x.get("request_status") == "RATE_LIMIT_429" for x in snapshot.values()
    )
    any_rate_limited = snapshot_rate_limited or individual["any_429"]
    output = {
        "schema": "SKY_FUGLE_TWO_STAGE_ACCEPTANCE_V1",
        "checked_at_tpe": checked.isoformat(),
        "source": "Fugle paid REST, existing FUGLE_API_KEY from GitHub Actions secret",
        "snapshot": snapshot,
        "individual": individual,
        "research_only": True,
        "production_eligible": False,
        "full_market_executed_certified": False,
        "quota_verdict": ("RATE_LIMIT_OBSERVED" if any_rate_limited else
                          "NOT_TESTED_NO_QUOTE_CALLS" if individual["requests_made"] == 0 else
                          "NO_429_IN_BOUNDED_SAMPLE_LIMIT_NOT_CERTIFIED"),
        "quota_note": "8 spaced calls cannot establish contractual per-minute/day quota.",
        "trade_action": "禁止交易",
    }
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FUGLE_TWO_STAGE_AUDIT", "TSE", snapshot.get("TSE", {}).get("request_status"),
          "OTC", snapshot.get("OTC", {}).get("request_status"),
          "individual_calls", individual["requests_made"],
          "fresh", individual["fresh_executed"],
          "rate_observed", individual["any_429"], "NO_TRADE")


if __name__ == "__main__":
    main()
