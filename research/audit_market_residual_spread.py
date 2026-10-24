from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[1,3,5,10]
COSTS=[0.00,0.20,0.45]
FEATURES=["vol20","drawdown20"]

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:return None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals)}

def load_daily(history_dir):
    bysym={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"));sym=str(o["symbol"]);by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open"));cl=fnum(bars[-1].get("close"))
            hs=[fnum(x.get("high")) for x in bars if fnum(x.get("high")) is not None]
            if op is None or cl is None or not hs:continue
            days.append({"date":d,"open":op,"close":cl,"high":max(hs)})
        bysym[sym]=days
    return bysym

def stdev_rets(xs):
    rs=[xs[i]/xs[i-1]-1 for i in range(1,len(xs)) if xs[i-1]]
    return statistics.pstdev(rs)*100 if rs else None

def build_rows(bysym):
    raw=[]
    for sym,days in bysym.items():
        closes=[x["close"] for x in days]
        for i in range(20,len(days)-11):
            entry=days[i+1]["open"]
            if entry is None or entry>100:continue
            high20=max(x["high"] for x in days[i-19:i+1])
            vol20=stdev_rets(closes[i-19:i+1])
            if vol20 is None:continue
            rec={"symbol":sym,"date":days[i]["date"],
                 "vol20":vol20,
                 "drawdown20":(closes[i]/high20-1)*100 if high20 else None}
            for h in HORIZONS:
                rec[f"raw_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)
    bydate=defaultdict(list)
    for r in raw:bydate[r["date"]].append(r)
    out=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if r["vol20"] is not None and r["drawdown20"] is not None]
        if len(valid)<30:continue
        for h in HORIZONS:
            m=statistics.mean(r[f"raw_{h}d"] for r in valid)
            for r in valid:r[f"res_{h}d"]=r[f"raw_{h}d"]-m
        out.extend(valid)
    return out

def decile_stats(arr,feature,target,cost):
    xs=sorted([r for r in arr if r.get(feature) is not None and r.get(target) is not None], key=lambda r:r[feature])
    n=len(xs)
    if n<100:return {}
    out={}
    for d in range(10):
        lo=d*n//10;hi=(d+1)*n//10
        vals=[r[target]-cost for r in xs[lo:hi]]
        out[str(d+1)]=metrics(vals)
    return out

def daily_cross_section(rows,feature,target,cost,long_low=True):
    bydate=defaultdict(list)
    for r in rows:
        if r.get(feature) is not None and r.get(target) is not None:bydate[r["date"]].append(r)
    long_vals=[];short_vals=[];spreads=[]
    for d,arr in bydate.items():
        if len(arr)<30:continue
        s=sorted(arr,key=lambda r:r[feature]);k=max(1,len(s)//10)
        low=s[:k];high=s[-k:]
        if long_low:
            L=statistics.mean(r[target] for r in low)-cost
            S=statistics.mean(r[target] for r in high)-cost
        else:
            L=statistics.mean(r[target] for r in high)-cost
            S=statistics.mean(r[target] for r in low)-cost
        long_vals.append(L);short_vals.append(S)
        # diagnostic spread: no transaction-cost doubling beyond each leg cost
        spreads.append(L-S)
    return {"long_decile":metrics(long_vals),
            "opposite_decile":metrics(short_vals),
            "spread":metrics(spreads)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_residual_spread")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir))
    splits={"train":[r for r in rows if int(r["date"][:4])<=2024],
            "valid":[r for r in rows if int(r["date"][:4])==2025],
            "test":[r for r in rows if int(r["date"][:4])==2026]}
    report={"method":"Market-Residual Cross-Sectional Spread Audit",
            "horizons":HORIZONS,"costs":COSTS,"split_counts":{k:len(v) for k,v in splits.items()},
            "results":{},"production_eligible":False,
            "note":"Market-neutral spread is research-only; formal Sky Swing remains long-only.",
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","2026 previously observed; not fresh untouched OOS."]}
    for h in HORIZONS:
        t=f"res_{h}d"
        for f in FEATURES:
            if f=="drawdown20" and h!=1:continue
            key=f"{f}_{h}d";report["results"][key]={}
            for c in COSTS:
                ck=f"{c:.2f}";report["results"][key][ck]={}
                for sp,arr in splits.items():
                    report["results"][key][ck][sp]={
                        "cross_section":daily_cross_section(arr,f,t,c,long_low=(f=="vol20")),
                        "global_deciles":decile_stats(arr,f,t,c)}
    (out/"residual_spread_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Market-Residual Cross-Sectional Spread Audit",f"- Split counts: {report['split_counts']}"]
    for key,v in report["results"].items():
        lines.append(f"\n## {key} @0.20%")
        for sp in ("train","valid","test"):
            x=v["0.20"][sp]["cross_section"]
            lines.append(f"- {sp}: long={x['long_decile']} spread={x['spread']}")
    (out/"residual_spread_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
