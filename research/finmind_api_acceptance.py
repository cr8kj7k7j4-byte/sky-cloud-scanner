#!/usr/bin/env python3
"""Read-only FinMind entitlement/data acceptance. Never logs the token or trades."""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.finmindtrade.com/api/v4/data"
DATASETS = {
    "daily_price": ("TaiwanStockPrice", {"date", "stock_id", "open", "max", "min", "close", "Trading_Volume"}),
    "margin": ("TaiwanStockMarginPurchaseShortSale", {"date", "stock_id"}),
    "institutional": ("TaiwanStockInstitutionalInvestorsBuySell", {"date", "stock_id"}),
}
OUTPUT = pathlib.Path("research_output/finmind_acceptance.json")


def probe(name, dataset, required, token, start, end):
    params = urllib.parse.urlencode({"dataset": dataset, "data_id": "2330",
                                     "start_date": start, "end_date": end})
    request = urllib.request.Request(BASE + "?" + params,
                                     headers={"Authorization": "Bearer " + token,
                                              "Accept": "application/json",
                                              "User-Agent": "Sky-FinMind-ReadOnly-Acceptance/1.0"})
    result = {"dataset": dataset, "status": "FAIL", "rows": 0, "first_date": None,
              "last_date": None, "missing_columns": [], "reason": None}
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(4 * 1024 * 1024)
            status = response.status
        obj = json.loads(body)
        data = obj.get("data", []) if isinstance(obj, dict) else []
        msg = str(obj.get("msg", ""))[:160] if isinstance(obj, dict) else "unexpected_response"
        if status != 200 or not isinstance(data, list):
            result["reason"] = "invalid_http_or_data_shape"
        elif not data:
            result["reason"] = "empty_data_or_permission_not_confirmed: " + msg
        else:
            cols = set().union(*(row.keys() for row in data if isinstance(row, dict)))
            missing = sorted(required - cols)
            dates = sorted(str(row.get("date")) for row in data
                           if isinstance(row, dict) and row.get("date"))
            result.update(rows=len(data), missing_columns=missing,
                          first_date=dates[0] if dates else None,
                          last_date=dates[-1] if dates else None)
            result["status"] = "PASS" if not missing and dates else "FAIL"
            if result["status"] == "FAIL":
                result["reason"] = "missing_expected_columns_or_dates"
    except urllib.error.HTTPError as exc:
        result["reason"] = "HTTP_" + str(exc.code)
    except urllib.error.URLError as exc:
        result["reason"] = "network_failure:" + type(exc.reason).__name__
    except (ValueError, TimeoutError) as exc:
        result["reason"] = "response_error:" + type(exc).__name__
    except Exception as exc:
        result["reason"] = "unexpected_error:" + type(exc).__name__
    return name, result


def main():
    # PINNED historical dates: avoid treating a weekend/late update as an API failure.
    start, end = "2026-10-26", "2026-10-30"
    result = {
        "purpose": "read_only_entitlement_acceptance",
        "tested_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "symbol": "2330", "start_date": start, "end_date": end,
        "api_source": BASE, "token_present": bool(os.environ.get("FINMIND_TOKEN")),
        "results": {}, "overall": "FAIL", "promotion_status": "RESEARCH_ONLY",
    }
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    if token:
        for name, (dataset, required) in DATASETS.items():
            key, value = probe(name, dataset, required, token, start, end)
            result["results"][key] = value
    else:
        result["reason"] = "FINMIND_TOKEN_missing"
    result["overall"] = ("PASS" if len(result["results"]) == len(DATASETS)
                         and all(x["status"] == "PASS" for x in result["results"].values())
                         else "FAIL")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
