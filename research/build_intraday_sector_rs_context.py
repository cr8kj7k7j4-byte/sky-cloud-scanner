from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd


def _date(value):
    return pd.to_datetime(value,errors="coerce",utc=True).tz_convert("Asia/Taipei").date()


def _mapping_for(mapping: pd.DataFrame,symbol: str,day: date):
    x=mapping[mapping["symbol"].astype(str)==str(symbol)]
    if x.empty:
        return None
    day_ts=pd.Timestamp(day)
    starts=pd.to_datetime(x["effective_from"],errors="coerce")
    if "effective_to" in x.columns:
        ends=pd.to_datetime(x["effective_to"],errors="coerce")
    else:
        ends=pd.Series([pd.NaT]*len(x),index=x.index,dtype="datetime64[ns]")
    valid=x[(starts<=day_ts)&(ends.isna()|(ends>=day_ts))]
    if valid.empty:
        return None
    valid=valid.assign(_start=pd.to_datetime(valid["effective_from"],errors="coerce"))
    return valid.sort_values("_start").iloc[-1]


def build_sector_rs_context(
    decisions: pd.DataFrame,
    stock_returns: pd.DataFrame,
    mapping: pd.DataFrame,
    market_context: pd.DataFrame,
) -> tuple[pd.DataFrame,dict]:
    """
    Pure data-layer Sector RS.

    decisions:
      decision_id, symbol, decision_timestamp

    stock_returns:
      observation_timestamp, symbol, stock_return
      Must contain the full contemporaneous cross-section, not only candidates.

    mapping:
      symbol, sector, effective_from, effective_to

    market_context:
      decision_id, market_return
    """
    d=decisions.copy()
    d["decision_timestamp"]=pd.to_datetime(d["decision_timestamp"],errors="coerce",utc=True)
    r=stock_returns.copy()
    r["observation_timestamp"]=pd.to_datetime(r["observation_timestamp"],errors="coerce",utc=True)
    r["stock_return"]=pd.to_numeric(r["stock_return"],errors="coerce")
    m=market_context[["decision_id","market_return"]].copy()
    m["market_return"]=pd.to_numeric(m["market_return"],errors="coerce")
    market_by_id=m.set_index("decision_id")["market_return"].to_dict()

    out=[]; mapping_expected=0; mapping_observed=0
    for ts,part in d.groupby("decision_timestamp",dropna=False):
        if pd.isna(ts):
            for _,row in part.iterrows():
                out.append({"decision_id":row["decision_id"],"sector_rs_status":"MISSING"})
            continue
        day=ts.tz_convert("Asia/Taipei").date()
        cross=r[r["observation_timestamp"]==ts].copy()
        prepared=[]
        for _,row in cross.iterrows():
            mapping_expected+=1
            mr=_mapping_for(mapping,str(row["symbol"]),day)
            if mr is None:
                continue
            mapping_observed+=1
            prepared.append({
                "symbol":str(row["symbol"]),
                "sector":str(mr["sector"]),
                "sector_effective_from":str(mr["effective_from"]),
                "sector_effective_to":mr.get("effective_to"),
                "stock_return":float(row["stock_return"]),
            })
        px=pd.DataFrame(prepared)
        if px.empty:
            for _,row in part.iterrows():
                out.append({"decision_id":row["decision_id"],"sector_rs_status":"MISSING"})
            continue
        sec=px.groupby("sector",as_index=False)["stock_return"].mean().rename(
            columns={"stock_return":"sector_return"}
        )
        px=px.merge(sec,on="sector",how="left")
        lookup=px.set_index("symbol").to_dict("index")
        for _,row in part.iterrows():
            x=lookup.get(str(row["symbol"]))
            market=market_by_id.get(row["decision_id"])
            if x is None or market is None or pd.isna(market):
                out.append({"decision_id":row["decision_id"],"sector_rs_status":"MISSING"})
                continue
            out.append({
                "decision_id":row["decision_id"],
                "sector":x["sector"],
                "sector_effective_from":x["sector_effective_from"],
                "sector_effective_to":x["sector_effective_to"],
                "sector_return":float(x["sector_return"]),
                "sector_rs_vs_market":float(x["sector_return"])-float(market),
                "stock_rs_vs_sector":float(x["stock_return"])-float(x["sector_return"]),
                "sector_rs_status":"OK",
            })

    result=pd.DataFrame(out)
    decision_coverage=(
        float((result["sector_rs_status"]=="OK").mean())
        if len(result) and "sector_rs_status" in result else 0.0
    )
    mapping_coverage=mapping_observed/mapping_expected if mapping_expected else 0.0
    report={
        "schema_version":"INTRADAY_SECTOR_RS_CONTEXT_V1_0",
        "decision_rows":int(len(result)),
        "decision_coverage":round(decision_coverage,6),
        "cross_section_mapping_coverage":round(mapping_coverage,6),
        "status":"PASS" if decision_coverage>=0.95 and mapping_coverage>=0.95 else "BLOCKED",
        "governance":{
            "full_contemporaneous_cross_section_required":True,
            "future_sector_mapping_allowed":False,
            "alpha_thresholds_applied":False,
            "trade_gate_generated":False,
        },
    }
    return result,report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--stock-returns",required=True)
    ap.add_argument("--sector-mapping",required=True)
    ap.add_argument("--market-context",required=True)
    ap.add_argument("--out-dir",default="research_output/intraday_sector_rs")
    args=ap.parse_args()

    frame,report=build_sector_rs_context(
        pd.read_csv(args.decisions),
        pd.read_csv(args.stock_returns),
        pd.read_csv(args.sector_mapping),
        pd.read_csv(args.market_context),
    )
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"sector_context.csv",index=False)
    (out/"sector_rs_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
