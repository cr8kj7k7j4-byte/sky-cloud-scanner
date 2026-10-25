from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE="https://api.fugle.tw/marketdata/v1.0/stock"
TAIEX_SYMBOL="IX0001"
MIN_INTERVAL=1.10


def _headers():
    key=os.getenv("FUGLE_API_KEY","").strip()
    if not key:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY":key,"User-Agent":"SkyCloudScanner-MarketBenchmark/1.0"}


def _chunks(start: date,end: date,max_days: int=330):
    cur=start
    while cur<=end:
        nxt=min(end,cur+timedelta(days=max_days))
        yield cur,nxt
        cur=nxt+timedelta(days=1)


def download_taiex(from_date: str,to_date: str,request_get=requests.get,sleep_fn=time.sleep):
    start=date.fromisoformat(from_date)
    end=date.fromisoformat(to_date)
    rows=[]
    for a,b in _chunks(start,end):
        url=f"{BASE}/historical/candles/{TAIEX_SYMBOL}"
        params={
            "from":a.isoformat(),"to":b.isoformat(),"timeframe":"5",
            "fields":"open,high,low,close,volume,average","sort":"asc",
        }
        t0=time.time()
        r=request_get(url,params=params,headers=_headers(),timeout=30)
        if r.status_code==404:
            data=[]
        else:
            r.raise_for_status()
            payload=r.json()
            data=payload.get("data",[]) if isinstance(payload,dict) else []
        rows.extend(data)
        elapsed=time.time()-t0
        if elapsed<MIN_INTERVAL:
            sleep_fn(MIN_INTERVAL-elapsed)
    return rows


def build_decision_benchmark(decisions: pd.DataFrame,bars: list[dict]) -> pd.DataFrame:
    b=pd.DataFrame(bars)
    if b.empty:
        return pd.DataFrame(columns=["decision_id","market_return","market_benchmark_symbol","market_benchmark_cutoff"])
    b["timestamp"]=pd.to_datetime(b["date"],errors="coerce",utc=True)
    for c in ("open","close"):
        b[c]=pd.to_numeric(b[c],errors="coerce")
    b=b[b["timestamp"].notna()].sort_values("timestamp")
    b["session_date"]=b["timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    d=decisions.copy()
    d["decision_timestamp"]=pd.to_datetime(d["decision_timestamp"],errors="coerce",utc=True)
    if "session_date" not in d.columns:
        d["session_date"]=d["decision_timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    out=[]
    for _,row in d.iterrows():
        ts=row["decision_timestamp"]
        day=str(row["session_date"])
        part=b[(b["session_date"]==day)&(b["timestamp"]<=ts)]
        if part.empty:
            out.append({
                "decision_id":row["decision_id"],"market_return":None,
                "market_benchmark_symbol":TAIEX_SYMBOL,"market_benchmark_cutoff":None,
            })
            continue
        first=part.iloc[0]
        last=part.iloc[-1]
        op=float(first["open"]) if pd.notna(first["open"]) else None
        close=float(last["close"]) if pd.notna(last["close"]) else None
        ret=(close/op-1.0) if op not in (None,0) and close is not None else None
        out.append({
            "decision_id":row["decision_id"],
            "market_return":ret,
            "market_benchmark_symbol":TAIEX_SYMBOL,
            "market_benchmark_cutoff":last["timestamp"].isoformat(),
        })
    return pd.DataFrame(out)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--from-date",required=True)
    ap.add_argument("--to-date",required=True)
    ap.add_argument("--decisions")
    ap.add_argument("--out-dir",default="research_output/taiex_benchmark")
    args=ap.parse_args()

    bars=download_taiex(args.from_date,args.to_date)
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    (out/"IX0001_5m.json").write_text(
        json.dumps({
            "symbol":TAIEX_SYMBOL,"name":"發行量加權股價指數",
            "timeframe":"5","from":args.from_date,"to":args.to_date,"data":bars,
        },ensure_ascii=False),encoding="utf-8"
    )
    report={
        "schema_version":"TAIEX_BENCHMARK_V1_0",
        "symbol":TAIEX_SYMBOL,
        "bars":len(bars),
        "from":args.from_date,"to":args.to_date,
        "status":"PASS" if bars else "FAIL",
        "source":"Fugle historical candles",
    }
    if args.decisions:
        decisions=pd.read_csv(args.decisions)
        frame=build_decision_benchmark(decisions,bars)
        frame.to_csv(out/"market_benchmark.csv",index=False)
        report["decision_rows"]=len(frame)
        report["decision_coverage"]=round(float(frame["market_return"].notna().mean()),6) if len(frame) else 0.0
    (out/"benchmark_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
