"""Low-volume, read-only live Fugle API entitlement probe for Stage-2.

Does not infer plan quota from a successful sample or certify whole-market scope.
Never prints credentials or raw provider payloads.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from src.realtime_quote_evidence import fugle_executed_trade

TPE = ZoneInfo("Asia/Taipei")
BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
OUTPUT = Path("output/fugle_stage2_probe/latest.json")


def check(response, label, *, quote=False):
    result = {"endpoint": label, "http_status": response.status_code,
              "api_accessible": response.status_code == 200}
    if response.status_code != 200:
        result["outcome"] = ("RATE_LIMITED" if response.status_code == 429 else
                             "PLAN_RESTRICTED" if response.status_code in (401, 403) else
                             "HTTP_ERROR")
        return result
    try:
        payload = response.json()
    except ValueError:
        result["outcome"] = "INVALID_JSON"
        return result
    if not isinstance(payload, dict):
        result["outcome"] = "INVALID_PAYLOAD"
        return result
    if quote:
        q = payload.get("data", payload)
        if not isinstance(q, dict):
            result["outcome"] = "INVALID_QUOTE"
            return result
        price, timestamp, status = fugle_executed_trade(q, max_age_seconds=180)
        result.update({"outcome": status, "last_trade_time": timestamp.isoformat() if timestamp else None,
                       "verified_trade_price": price, "last_trade_time_field_present":
                       isinstance(q.get("lastTrade"), dict) and q["lastTrade"].get("time") is not None,
                       "quote_date": q.get("date")})
    else:
        data = payload.get("data")
        result.update({"outcome": "AVAILABLE" if isinstance(data, list) else "INVALID_SNAPSHOT",
                       "row_count": len(data) if isinstance(data, list) else None,
                       "provider_date": payload.get("date")})
    return result


def run(request=None, sleeper=time.sleep):
    request = request or requests.get
    now = datetime.now(TPE)
    results = []
    token = os.getenv("FUGLE_API_KEY", "").strip()
    if not token:
        return {"status": "MISSING_SECRET", "results": [],
                "production_eligible": False, "automatic_order": False}
    headers = {"X-API-KEY": token, "User-Agent": "SkyStage2Probe/1.0"}
    targets = [("snapshot_TSE", "/snapshot/quotes/TSE", {"type": "COMMONSTOCK"}, False),
               ("snapshot_OTC", "/snapshot/quotes/OTC", {"type": "COMMONSTOCK"}, False),
               ("quote_2330_TSE", "/intraday/quote/2330", None, True),
               ("quote_8089_OTC", "/intraday/quote/8089", None, True)]
    start = time.monotonic()
    for label, path, params, is_quote in targets:
        try:
            response = request(BASE + path, params=params, headers=headers, timeout=20)
            results.append(check(response, label, quote=is_quote))
        except requests.RequestException as exc:
            results.append({"endpoint": label, "api_accessible": False,
                            "outcome": "NETWORK_ERROR", "error_type": type(exc).__name__})
        sleeper(0.5)
    quote_results = [x for x in results if x["endpoint"].startswith("quote_")]
    quote_access = all(x.get("api_accessible") for x in quote_results)
    quote_timestamp = all(x.get("last_trade_time_field_present") for x in quote_results)
    return {
        "schema": "SKY_FUGLE_STAGE2_ENTITLEMENT_PROBE_V1",
        "tested_at_tpe": now.isoformat(),
        "request_count": len(results),
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "results": results,
        "intraday_quote_access_both_markets": quote_access,
        "intraday_last_trade_time_present_both": quote_timestamp,
        "rate_limit_status": "INSUFFICIENT_SAMPLE_FOR_PLAN_LIMIT",
        "stage2_integrated": False,
        "production_eligible": False, "automatic_order": False,
    }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result = run()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
