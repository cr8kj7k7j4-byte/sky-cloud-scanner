"""Fugle Developer API: historical market-data provenance and replay readiness.

Read-only, no orders or trading signals. Requires FUGLE_API_KEY in GitHub Actions
secrets. Scrubs secrets and API response bodies from reports. Tests daily raw/
adjusted 1y candles, limited historical 5-minute candles, and independent
FinMind daily-price closing overlap; does not infer event publish timestamps.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/"
FINMIND = "https://api.finmindtrade.com/api/v4/data"
START, END = "2025-11-10", "2026-11-06"
SYMBOLS = ("0050", "1101", "2330", "8088")
MINUTE_SYMBOLS = ("1101", "8088")
MISMATCH_TOLERANCE_PCT = 0.02  # cross-feed raw close tolerance, not an entry rule


def request_json(url: str, headers: dict, *, attempts: int = 3):
    for n in range(attempts):
        try:
            with urlopen(Request(url, headers=headers), timeout=28) as response:
                return json.load(response), {"http": response.status}
        except HTTPError as exc:
            error = {"http": exc.code}
            if exc.code not in (429, 500, 502, 503, 504) or n == attempts - 1:
                return None, error
        except (TimeoutError, URLError, OSError, ValueError) as exc:
            error = {"error_type": type(exc).__name__}
            if n == attempts - 1:
                return None, error
        time.sleep(n + 1)
    return None, {"error_type": "UNKNOWN"}


def candles(key, symbol, start, end, *, timeframe="D", adjusted=False):
    params = {"from": start, "to": end, "timeframe": timeframe,
              "sort": "asc", "fields": "open,high,low,close,volume"}
    if timeframe == "D":
        params["adjusted"] = str(bool(adjusted)).lower()
    url = BASE + symbol + "?" + urlencode(params)
    return request_json(url, {"X-API-KEY": key, "User-Agent": "SkyFugleResearchAudit/1.0"})


def clean_rows(payload, *, intraday=False):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return {}, {"schema_ok": False, "errors": ["NO_DATA_ARRAY"]}
    rows = {}
    bad = 0
    for item in payload["data"]:
        try:
            d = item["date"]
            o, hi, lo, c, v = (float(item[name]) for name in ("open", "high", "low", "close", "volume"))
            if not (isinstance(d, str) and len(d) >= (19 if intraday else 10)
                    and all(math.isfinite(x) for x in (o, hi, lo, c, v))
                    and min(o, hi, lo, c) > 0 and v >= 0 and lo <= min(o, c) <= hi
                    and lo <= max(o, c) <= hi):
                raise ValueError("invalid OHLCV")
            if intraday:
                time_seen = datetime.fromisoformat(d.replace("Z", "+00:00"))
                if time_seen.tzinfo is None:
                    raise ValueError("intraday missing timezone")
            rows[d] = {"open": o, "high": hi, "low": lo, "close": c, "volume": v}
        except (KeyError, TypeError, ValueError):
            bad += 1
    return rows, {"schema_ok": len(rows) > 0 and bad == 0,
                  "valid_rows": len(rows), "invalid_rows": bad,
                  "duplicate_or_repeated_dates": len(payload["data"]) - len(rows) - bad,
                  "first_date": min(rows) if rows else None,
                  "last_date": max(rows) if rows else None}


def finmind_closes(symbol, token):
    q = urlencode({"dataset": "TaiwanStockPrice", "data_id": symbol,
                   "start_date": START, "end_date": END})
    h = {"User-Agent": "SkyFugleResearchAudit/1.0"}
    if token:
        h["Authorization"] = "Bearer " + token
    payload, state = request_json(FINMIND + "?" + q, h)
    out = {}
    if isinstance(payload, dict) and payload.get("status") == 200:
        for row in payload.get("data", []):
            try:
                d, price = str(row["date"]), float(row["close"])
                if math.isfinite(price) and price > 0:
                    out[d] = price
            except (KeyError, ValueError, TypeError):
                continue
    return out, state


def cross_check(raw, reference):
    common = sorted(set(raw) & set(reference))
    deltas = [abs(raw[d]["close"] / reference[d] - 1) * 100 for d in common]
    return {
        "reference": "FinMind TaiwanStockPrice daily CLOSE",
        "common_sessions": len(common),
        "max_abs_raw_close_difference_pct": round(max(deltas), 4) if deltas else None,
        "mismatch_sessions_above_0_02pct": sum(x > MISMATCH_TOLERANCE_PCT for x in deltas),
        "same_date_close_match": bool(common) and not any(x > MISMATCH_TOLERANCE_PCT for x in deltas),
        "caveat": "Daily OHLCV and close comparisons do not certify intraday execution, dividends, corporate actions, or event disclosure times.",
    }


def audit(key, finmind_token):
    result = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "research_window": [START, END],
        "model": "FUGLE_DEVELOPER_HISTORICAL_EVIDENCE_AUDIT",
        "production_signal": False, "strategy_positive_expectancy_verified": False,
        "event_pit_verified": False,
        "fugle_key_present": bool(key),
        "status": "INSUFFICIENT_DATA",
        "per_symbol": {},
        "minute_sample": {},
        "notes": [
            "Fugle historical candles are market prices, not historical MOPS issuer published_at.",
            "Developer REST API is distinct from connected Fugle app content-spec access.",
            "Raw OHLC is for next-open hypothetical fills, adjusted OHLC only for corporate-action comparison.",
            "This is a data/replay audit, NOT an independent positive-expectancy strategy backtest.",
            "Requires separate PIT event ledger, delisted-universe coverage and portfolio/transaction cost replay."
        ],
    }
    if not key:
        result["blocked_reason"] = "FUGLE_API_KEY_NOT_CONFIGURED_IN_GITHUB_RUNNER"
        return result
    for symbol in SYMBOLS:
        raw_p, raw_http = candles(key, symbol, START, END)
        adj_p, adj_http = candles(key, symbol, START, END, adjusted=True)
        raw, raw_q = clean_rows(raw_p)
        adj, adj_q = clean_rows(adj_p)
        fin, fin_http = finmind_closes(symbol, finmind_token)
        same = set(raw) & set(adj)
        adjustment_changed = sum(abs(raw[d]["close"] / adj[d]["close"] - 1) > 1e-7 for d in same)
        result["per_symbol"][symbol] = {
            "raw_http": raw_http, "raw": raw_q, "adjusted_http": adj_http,
            "adjusted": adj_q,
            "adjusted_returned": bool(isinstance(adj_p, dict) and adj_p.get("adjusted") is True),
            "common_raw_adjusted_days": len(same),
            "raw_adjusted_price_diff_days": adjustment_changed,
            "finmind_http": fin_http,
            "finmind_crosscheck": cross_check(raw, fin),
            "historical_issuer_published_at_provided": False,
        }
    for symbol in MINUTE_SYMBOLS:
        payload, state = candles(key, symbol, "2026-11-06", "2026-11-06", timeframe="5")
        rows, quality = clean_rows(payload, intraday=True)
        result["minute_sample"][symbol] = {
            "request_http": state, "data": quality,
            "historical_trade_aggressor_side": False,
            "intraday_orderbook_5_levels": False,
            "note": "5m OHLCV alone cannot identify historical initiating buy orders or seller exhaustion."
        }
    result["price_audit_pass"] = all(
        x["raw"]["schema_ok"] and x["adjusted"]["schema_ok"]
        for x in result["per_symbol"].values())
    result["all_cross_source_close_match"] = all(
        x["finmind_crosscheck"]["same_date_close_match"]
        for x in result["per_symbol"].values())
    result["minute_data_audit_pass"] = all(
        x["data"]["schema_ok"] for x in result["minute_sample"].values())
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="research_output/fugle_historical_evidence.json")
    args = p.parse_args()
    result = audit(os.getenv("FUGLE_API_KEY", "").strip(),
                   os.getenv("FINMIND_API_TOKEN", "").strip())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "fugle_key_present": result["fugle_key_present"],
        "price_audit_pass": result.get("price_audit_pass"),
        "minute_data_audit_pass": result.get("minute_data_audit_pass"),
        "all_cross_source_close_match": result.get("all_cross_source_close_match"),
        "symbols": result["per_symbol"],
        "minute_sample": result["minute_sample"]
    }, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
