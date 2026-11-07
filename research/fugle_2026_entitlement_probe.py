"""Read-only Fugle historical 5-minute entitlement probe for six-model study.

Never prints API keys, headers, raw market data or query URLs. This is not a backtest.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

START, END = "2026-01-01", "2026-11-07"
BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
SYMBOLS = ("1101", "8088")


def summarize_candles(data):
    if not isinstance(data, list):
        raise ValueError("invalid_candle_data_type")
    parsed = []
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            raise ValueError("invalid_candle_timestamp")
        if any(row.get(field) is None for field in ("open", "high", "low", "close", "volume")):
            raise ValueError("missing_required_ohlcv")
        parsed.append(row["date"])
    if len(parsed) != len(set(parsed)):
        raise ValueError("duplicate_candle_timestamps")
    return {"bar_count": len(parsed), "first_timestamp": min(parsed) if parsed else None,
            "last_timestamp": max(parsed) if parsed else None}


def run_probe(api_key, symbols=SYMBOLS, get=None):
    if get is None:
        import requests
        get = requests.get
    results = []
    for symbol in symbols:
        result = {"symbol": symbol, "endpoint": "historical/candles",
                  "timeframe_minutes": 5, "requested_from": START, "requested_to": END}
        if not api_key:
            result.update({"status": "MISSING_CREDENTIAL", "permission_verified": False})
        else:
            try:
                response = get(
                    f"{BASE}/historical/candles/{symbol}",
                    params={"from": START, "to": END, "timeframe": "5",
                            "fields": "open,high,low,close,volume,average", "sort": "asc"},
                    headers={"X-API-KEY": api_key, "User-Agent": "Sky-Research-Probe/1.0"},
                    timeout=30,
                )
                code = int(response.status_code)
                result["http_status"] = code
                if code == 200:
                    summary = summarize_candles(response.json().get("data"))
                    result.update(summary)
                    result["permission_verified"] = summary["bar_count"] > 0
                    result["status"] = "DATA_RETURNED" if result["permission_verified"] else "EMPTY_RESPONSE"
                elif code in (401, 403):
                    result.update({"status": "AUTH_OR_PLAN_RESTRICTED",
                                   "permission_verified": False})
                elif code == 429:
                    result.update({"status": "RATE_LIMITED", "permission_verified": False})
                else:
                    result.update({"status": "HTTP_ERROR", "permission_verified": False})
            except (ValueError, TypeError, KeyError):
                result.update({"status": "INVALID_DATA", "permission_verified": False})
            except Exception:
                # Scrub exception strings: SDKs or proxy URLs sometimes include credentials.
                result.update({"status": "TRANSPORT_ERROR", "permission_verified": False})
        results.append(result)
    return {
        "schema": "SKY_FUGLE_2026_HISTORICAL_ENTITLEMENT_PROBE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_period": {"start": START, "end": END},
        "results": results,
        "all_symbols_retrieved": all(x["permission_verified"] for x in results),
        "limited_two_symbol_probe_only": True,
        "all_market_coverage_verified": False,
        "complete_period_verified": False,
        "backtest_executed": False,
        "production_changed": False,
        "next_action": "Audit per-symbol per-session coverage and actual model provenance before full backtests."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="research_output/fugle_2026_entitlement_probe.json")
    args = parser.parse_args()
    output = run_probe(os.environ.get("FUGLE_API_KEY", "").strip())
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DATA_RETURNED" if output["all_symbols_retrieved"] else "INCOMPLETE",
                      "results": output["results"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
