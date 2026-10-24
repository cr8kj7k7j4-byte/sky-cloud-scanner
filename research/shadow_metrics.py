from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def profit_factor(r):
    vals=np.asarray(r,dtype=float)
    gains=vals[vals>0].sum()
    losses=abs(vals[vals<0].sum())
    if losses==0:
        return float("inf") if gains>0 else 0.0
    return float(gains/losses)


def max_drawdown_r(r):
    vals=np.asarray(r,dtype=float)
    if vals.size==0:
        return 0.0
    eq=np.cumsum(vals)
    peaks=np.maximum.accumulate(eq)
    return float(abs((eq-peaks).min()))


def summarize(df):
    if df.empty:
        return {"trades":0,"expectancy_r":0.0,"profit_factor":0.0,"max_drawdown_r":0.0,"mae_r_p95":0.0,"mfe_r_median":0.0,"regime_count":0}
    r=pd.to_numeric(df["r_multiple"],errors="coerce").dropna()
    mae=pd.to_numeric(df["mae_r"],errors="coerce").dropna()
    mfe=pd.to_numeric(df["mfe_r"],errors="coerce").dropna()
    pf=profit_factor(r)
    return {
        "trades": int(len(r)),
        "expectancy_r": round(float(r.mean()) if len(r) else 0.0,6),
        "profit_factor": round(pf,6) if np.isfinite(pf) else "inf",
        "max_drawdown_r": round(max_drawdown_r(r),6),
        "mae_r_p95": round(float(mae.quantile(0.95)) if len(mae) else 0.0,6),
        "mfe_r_median": round(float(mfe.median()) if len(mfe) else 0.0,6),
        "positive_r_share": round(float((r>0).mean()) if len(r) else 0.0,6),
        "regime_count": int(df["regime"].dropna().nunique()) if "regime" in df.columns else 0,
    }


def by_regime(df):
    if "regime" not in df.columns:
        return {}
    return {str(k):summarize(v) for k,v in df.groupby("regime")}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="research_output/shadow_metrics.json")
    args=ap.parse_args()

    rows=[]
    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    df=pd.DataFrame(rows)
    report={
        "overall": summarize(df),
        "by_regime": by_regime(df),
        "note":"Shadow metrics are observational evidence, not live-trading performance."
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
