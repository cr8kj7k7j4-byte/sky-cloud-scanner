#!/usr/bin/env python3
"""Read-only parameterized FinMind query; no token or orders in output."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://api.finmindtrade.com/api/v4/data"
DATASETS = {
    "price": "TaiwanStockPrice",
    "margin": "TaiwanStockMarginPurchaseShortSale",
    "institutional": "TaiwanStockInstitutionalInvestorsBuySell",
}
OUT = Path("research_output/finmind_query_result.json")


def read_api(dataset, symbol, start, end, token):
    query = urllib.parse.urlencode({"dataset": dataset, "data_id": symbol,
                                    "start_date": start, "end_date": end})
    req = urllib.request.Request(
        ENDPOINT + "?" + query,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/json",
                 "User-Agent": "Sky-Readonly-FinMind-Query/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read(6_000_000)
    obj = json.loads(body)
    if not isinstance(obj, dict) or not isinstance(obj.get("data"), list):
        return {"status": "FAIL", "reason": "invalid_response_structure"}
    rows = obj["data"]
    if not rows:
        return {"status": "FAIL", "reason": "empty_dataset_or_permission"}
    dates = sorted({str(row.get("date", "")) for row in rows if isinstance(row, dict)})
    dates = [d for d in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
    columns = sorted({key for row in rows if isinstance(row, dict) for key in row})
    if not dates or not all(start <= d <= end for d in dates):
        return {"status": "FAIL", "reason": "invalid_dates"}
    return {"status": "PASS", "rows": len(rows),
            "first_date": dates[0], "last_date": dates[-1],
            "columns": columns,
            "latest_rows": [row for row in rows if row.get("date") == dates[-1]][:12]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="2330")
    p.add_argument("--start", default="2026-10-01")
    p.add_argument("--end", default="2026-11-06")
    args = p.parse_args()
    if not re.fullmatch(r"\d{4,6}", args.symbol):
        p.error("symbol must be 4 to 6 digits")
    try:
        start, end = (dt.date.fromisoformat(d) for d in (args.start, args.end))
    except ValueError:
        p.error("dates must be YYYY-MM-DD")
    if end < start or (end - start).days > 366 or end > dt.date.today():
        p.error("date range invalid, future, or longer than 366 days")
    result = {"source": ENDPOINT, "symbol": args.symbol,
              "query_start": str(start), "query_end": str(end),
              "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "research_only": True, "datasets": {}, "overall": "FAIL"}
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    if not token:
        result["reason"] = "missing_secret"
    else:
        for short, dataset in DATASETS.items():
            try:
                result["datasets"][short] = read_api(
                    dataset, args.symbol, str(start), str(end), token)
            except urllib.error.HTTPError as exc:
                result["datasets"][short] = {"status": "FAIL", "reason": "HTTP_" + str(exc.code)}
            except (urllib.error.URLError, TimeoutError):
                result["datasets"][short] = {"status": "FAIL", "reason": "network_or_timeout"}
            except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
                result["datasets"][short] = {
                    "status": "FAIL", "reason": "invalid_result_" + type(exc).__name__}
    result["overall"] = ("PASS" if len(result["datasets"]) == len(DATASETS)
                         and all(x["status"] == "PASS" for x in result["datasets"].values())
                         else "FAIL")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
