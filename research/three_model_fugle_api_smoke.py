"""Read-only real Fugle historical API acceptance check; no raw market data in logs.
Runs only in research branch; no GCP permissions, order actions, or model promotion.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from research.three_model_fugle_pipeline import read_fugle
TPE = timezone(timedelta(hours=8))
DEFAULT_END = date(2026, 11, 6)
SYMBOLS = ("1101", "8088")

def check_one(symbol: str, timeframe: str, end: date, key: str) -> dict:
    start = end if timeframe == "5" else end - timedelta(days=20)
    bars = read_fugle(symbol, timeframe, start, end, key)
    if not bars:
        raise ValueError("empty_response")
    if len({bar["timestamp"] for bar in bars}) != len(bars):
        raise ValueError("duplicate_timestamps")
    expected = "lots" if timeframe == "5" else "shares"
    if any(bar.get("volume_unit") != expected for bar in bars):
        raise ValueError("unexpected_volume_unit")
    last = datetime.fromisoformat(bars[-1]["timestamp"]).astimezone(TPE).date()
    if last > end:
        raise ValueError("future_bar")
    # Public audit deliberately excludes prices, volumes, full timestamps and key.
    return {"symbol":symbol, "timeframe":timeframe, "rows":len(bars),
            "latest_data_date":last.isoformat(), "volume_unit":expected,
            "schema_ohlcv":"PASS", "historical_only":True}

def main() -> int:
    out=Path("output/three_model_fugle_api_smoke_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    key=os.environ.get("FUGLE_API_KEY","")
    end=date.fromisoformat(os.environ.get("RESEARCH_END_DATE", DEFAULT_END.isoformat()))
    # Fixed past completed day: no live/intraday representation.
    if end > datetime.now(TPE).date()-timedelta(days=1):
        raise ValueError("end_date_must_be_past")
    report={"schema":"sky-fugle-readonly-api-smoke-v1",
            "end_date_requested":end.isoformat(),"historical_only":True,
            "market_data_republished":False,"orders":False,
            "production_signal":False,"trained_model_verified":False,
            "results":[],"status":"FAIL"}
    if not key:
        report["reason"]="missing_FUGLE_API_KEY"
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        return 2
    errors=[]
    for symbol in SYMBOLS:
        for tf in ("D","5"):
            try:
                row=check_one(symbol,tf,end,key)
                report["results"].append({"status":"PASS",**row})
            except Exception as exc:
                # Error class only: HTTPError details or secrets are never shown.
                errors.append({"symbol":symbol,"timeframe":tf,
                               "status":"FAIL","reason_type":type(exc).__name__})
                report["results"].append(errors[-1])
    report["status"]="PASS" if not errors else "FAIL"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FUGLE_HISTORICAL_READONLY_SMOKE:",report["status"])
    for row in report["results"]:
        print("SYMBOL",row["symbol"],"TIMEFRAME",row["timeframe"],
              "STATUS",row["status"],"BAR_COUNT",row.get("rows","UNKNOWN"),
              "LAST_DATA_DATE",row.get("latest_data_date","UNKNOWN"),
              "ERROR_TYPE",row.get("reason_type","NONE"))
    print("No paid raw OHLCV printed. No GCS write, no Cloud Run, no orders.")
    return 0 if not errors else 1

if __name__=="__main__":
    sys.exit(main())
