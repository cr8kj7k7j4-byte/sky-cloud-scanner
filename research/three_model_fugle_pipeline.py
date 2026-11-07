"""Paid Fugle historical evidence -> research-only observations -> private GCS object ledger.

Manual-only. No auto orders, no deployment, no public market-data redistribution.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time as clock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research.three_model_research_signals import generate, verify_bars

TPE = timezone(timedelta(hours=8))
BASE = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/"

def normalize_response(symbol, timeframe, response, start, end):
    if not isinstance(response, dict) or response.get("symbol") != symbol or str(response.get("timeframe")) != timeframe:
        raise ValueError("provider_symbol_or_timeframe_mismatch")
    rows = response.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("provider_empty_data")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid_provider_row")
        stamp = row.get("date")
        if timeframe == "D":
            if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
                raise ValueError("invalid_provider_date")
            parsed = datetime.combine(date.fromisoformat(stamp), time(13, 30), tzinfo=TPE)
        else:
            if not isinstance(stamp, str):
                raise ValueError("invalid_provider_datetime")
            parsed = datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if parsed.utcoffset() is None:
                raise ValueError("missing_market_timezone")
            parsed = parsed.astimezone(TPE)
        if not start <= parsed.date() <= end:
            raise ValueError("provider_date_outside_requested_window")
        normalized = {key: row.get(key) for key in ("open","high","low","close","volume")}
        normalized["timestamp"] = parsed.isoformat()
        result.append(normalized)
    result.sort(key=lambda x:x["timestamp"])
    verify_bars(result, datetime.combine(end, time(23,59),tzinfo=TPE), 1)
    return result

def read_fugle(symbol, timeframe, start, end, key, get=None):
    if not key:
        raise RuntimeError("missing_fugle_api_key")
    if not re.fullmatch(r"\d{4,5}", symbol):
        raise ValueError("invalid_symbol")
    if (end - start).days >= 365 or end < start:
        raise ValueError("invalid_date_span")
    params = {"from":start.isoformat(),"to":end.isoformat(),"timeframe":timeframe,
              "fields":"open,high,low,close,volume","sort":"asc"}
    req = Request(BASE + symbol + "?" + urlencode(params),
                  headers={"X-API-KEY":key,"User-Agent":"Sky-Three-Model-Research/1.0"})
    for attempt in range(2):
        try:
            if get is None:
                with urlopen(req, timeout=30) as response:
                    body = json.load(response)
            else:
                body = get(req)
            return normalize_response(symbol,timeframe,body,start,end)
        except HTTPError as ex:
            if ex.code == 429 and attempt == 0:
                clock.sleep(3)
                continue
            raise RuntimeError("fugle_http_" + str(ex.code)) from None
        except URLError:
            raise RuntimeError("fugle_network_failure") from None
    raise RuntimeError("fugle_retry_exhausted")

def upload_immutable(store, bucket, prefix, report):
    """One object per observation; create-only is idempotent across replays."""
    if not bucket or not re.fullmatch(r"[a-zA-Z0-9][\w.\-]{2,220}",bucket):
        raise ValueError("missing_or_invalid_private_bucket")
    if not prefix or not re.fullmatch(r"[A-Za-z0-9_/-]+",prefix) or ".." in prefix:
        raise ValueError("invalid_prefix")
    result=[]
    for row in report["observations"]:
        # Rejected/no-trade observations must also enter the immutable ledger.
        # Their stable IDs use the requested research date and rejection reasons,
        # not a transient workflow execution timestamp.
        identity = [row.get("model_id"), row.get("symbol"),
                    report.get("requested_end_date"), row.get("rejection_reasons", [])]
        record_id = row.get("signal_id") or ("rejected-" + hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24])
        key=f"{prefix.strip('/')}/{row['model_id']}/{row['symbol']}/{record_id}.json"
        blob=store.bucket(bucket).blob(key)
        canonical={k:v for k,v in row.items() if k != "as_of"}
        canonical["ledger_record_id"]=record_id
        data=json.dumps(canonical,sort_keys=True,ensure_ascii=False,separators=(",",":"))
        digest=hashlib.sha256(data.encode()).hexdigest()
        try:
            blob.upload_from_string(data,content_type="application/json",if_generation_match=0)
            status="CREATED"
        except Exception as exc:
            # A duplicate must be distinguished from a transient or permission error.
            if type(exc).__name__ != "PreconditionFailed":
                raise
            status="ALREADY_EXISTS_IDENTICAL"
        stored=blob.download_as_bytes()
        if hashlib.sha256(stored).hexdigest()!=digest:
            raise ValueError("ledger_identity_conflict")
        result.append({"model_id":row["model_id"],"symbol":row["symbol"],
                       "signal_id":row.get("signal_id"),"ledger_record_id":record_id,
                       "status":status,
                       "object_sha256":digest})
    return result

def run(symbols, end, bucket, prefix, key, store, out):
    as_of=datetime.now(TPE)
    # Historical candles are refreshed after close. Avoid treating today's unfinished candles as final.
    last_allowed=as_of.date() if as_of.time()>=time(16,30) else as_of.date()-timedelta(days=1)
    if end > last_allowed:
        raise ValueError("historical_candles_not_yet_final")
    if not symbols or len(symbols)>10 or len(symbols)!=len(set(symbols)):
        raise ValueError("invalid_symbol_count")
    inputs={}
    for symbol in symbols:
        five=read_fugle(symbol,"5",end-timedelta(days=8),end,key)
        clock.sleep(1.05)
        daily=read_fugle(symbol,"D",end-timedelta(days=90),end,key)
        clock.sleep(1.05)
        inputs[symbol]={"name":None,"bars_5m":five,"bars_daily":daily}
    report=generate({"source":"FUGLE","as_of":as_of.isoformat(),"symbols":inputs})
    report["requested_end_date"]=end.isoformat()
    ledger=upload_immutable(store,bucket,prefix,report)
    audit={"checked_at_tpe":as_of.isoformat(),"source":"Fugle historical/candles",
           "provider_authenticated":True, "historical_not_intraday_live":True,
           "trained_model_used":False,"production_signal":False,"orders":False,
           "observations_total":len(report["observations"]),
           "rejected_count":sum(not o.get("signal_id") for o in report["observations"]),
           "saved_records":len(ledger),"storage_statuses":ledger,
           "symbols_requested":symbols,"end_date":end.isoformat(),
           "live_mobile_deployment_verified":False}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return audit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--bucket",default=os.environ.get("SKY_RESEARCH_GCS_BUCKET",""))
    p.add_argument("--prefix",default="three-model-research/v1")
    p.add_argument("--out",default="output/three_model_fugle_evidence_summary.json")
    args=p.parse_args()
    symbols=[s.strip() for s in args.symbols.split(",") if s.strip()]
    if not args.bucket:
        raise RuntimeError("private_gcs_bucket_not_configured")
    from google.cloud import storage
    result=run(symbols,date.fromisoformat(args.end),args.bucket,args.prefix,
               os.environ.get("FUGLE_API_KEY",""),storage.Client(),Path(args.out))
    print(json.dumps({"status":"PRIVATE_LEDGER_SAVED","count":result["saved_records"],
                      "production_signal":False},ensure_ascii=False))

if __name__=="__main__":
    main()
