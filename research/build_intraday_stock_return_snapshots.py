from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research.build_intraday_market_context import load_history_dir
from src.point_in_time_universe import universe_as_of

SCHEMA_VERSION="INTRADAY_STOCK_RETURN_SNAPSHOTS_V1_0"


def build_stock_return_snapshots(
    decisions: pd.DataFrame,
    bars: pd.DataFrame,
    pit_intervals: list[dict],
) -> tuple[pd.DataFrame,dict]:
    """
    Produce the full contemporaneous PIT cross-section used by Market and Sector RS.
    Return = latest close at/before decision / session first open - 1.
    """
    d=decisions.copy()
    d["decision_timestamp"]=pd.to_datetime(d["decision_timestamp"],errors="coerce",utc=True)
    if "session_date" not in d.columns:
        d["session_date"]=d["decision_timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    b=bars.copy()
    b["timestamp"]=pd.to_datetime(b["timestamp"],errors="coerce",utc=True)
    if "session_date" not in b.columns:
        b["session_date"]=b["timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    rows=[]; audits=[]
    unique=d[["decision_timestamp","session_date"]].drop_duplicates()
    for _,u in unique.iterrows():
        ts=u["decision_timestamp"]
        day=str(u["session_date"])
        if pd.isna(ts):
            continue
        members=universe_as_of(pit_intervals,day)
        expected={str(x["symbol"]) for x in members}
        part=b[
            (b["session_date"]==day)
            & b["symbol"].astype(str).isin(expected)
            & ((b["timestamp"] + pd.Timedelta(minutes=5))<=ts)
        ].copy()
        if part.empty:
            audits.append({
                "observation_timestamp":ts.isoformat(),
                "expected":len(expected),"observed":0,"coverage":0.0,
            })
            continue
        first=(
            part.sort_values("timestamp")
            .groupby("symbol",as_index=False)
            .head(1)[["symbol","open"]]
            .rename(columns={"open":"session_open"})
        )
        last=(
            part.sort_values("timestamp")
            .groupby("symbol",as_index=False)
            .tail(1)[["symbol","timestamp","close"]]
        )
        snap=last.merge(first,on="symbol",how="left")
        snap["stock_return"]=snap["close"]/snap["session_open"]-1.0
        snap=snap[snap["stock_return"].notna()]
        observed=set(snap["symbol"].astype(str))
        for _,r in snap.iterrows():
            rows.append({
                "observation_timestamp":ts.isoformat(),
                "session_date":day,
                "symbol":str(r["symbol"]),
                "stock_return":float(r["stock_return"]),
                "source_bar_start_timestamp":r["timestamp"].isoformat(),
                "source_cutoff_timestamp":(r["timestamp"] + pd.Timedelta(minutes=5)).isoformat(),
            })
        audits.append({
            "observation_timestamp":ts.isoformat(),
            "expected":len(expected),
            "observed":len(observed),
            "coverage":len(observed)/len(expected) if expected else 0.0,
        })

    out=pd.DataFrame(rows)
    cov=[x["coverage"] for x in audits]
    report={
        "schema_version":SCHEMA_VERSION,
        "snapshots":len(audits),
        "rows":len(out),
        "mean_coverage":round(sum(cov)/len(cov),6) if cov else 0.0,
        "minimum_coverage":round(min(cov),6) if cov else 0.0,
        "status":"PASS" if cov and min(cov)>=0.95 else "BLOCKED",
        "worst_snapshots":sorted(audits,key=lambda x:x["coverage"])[:30],
        "governance":{
            "pit_universe_required":True,
            "future_bars_used":False,
            "only_completed_5m_bars_used":True,
            "full_cross_section_required":True,
        },
    }
    return out,report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--pit-universe",required=True)
    ap.add_argument("--out-dir",default="research_output/intraday_stock_returns")
    args=ap.parse_args()

    decisions=pd.read_csv(args.decisions)
    bars=load_history_dir(args.history_dir)
    obj=json.loads(Path(args.pit_universe).read_text(encoding="utf-8"))
    intervals=obj if isinstance(obj,list) else obj.get("intervals",[])
    frame,report=build_stock_return_snapshots(decisions,bars,intervals)
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"stock_return_snapshots.csv",index=False)
    (out/"stock_return_snapshots_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
