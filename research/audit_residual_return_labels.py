from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[3,5,10]
FEATURES=["trend_ma20","trend_ma60","vol20","drawdown20","ret20_rank","market_breadth20"]

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:return None

def pearson(x,y):
    if len(x)<3:return None
    mx=statistics.mean(x); my=statistics.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx=sum((a-mx)**2 for a in x); dy=sum((b-my)**2 for b in y)
    if dx<=0 or dy<=0:return None
    return num/(dx*dy)**0.5

def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i:vals[i]); out=[0.0]*len(vals); i=0
    while i<len(order):
        j=i
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]: j+=1
        rr=(i+j)/2
        for k in range(i,j+1): out[order[k]]=rr
        i=j+1
    return out

def spearman(x,y):
    return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def load_daily(history_dir):
    bysym={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:
                by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            hs=[fnum(x.get("high")) for x in bars if fnum(x.get("high")) is not None]
            if op is None or cl is None or not hs: continue
            days.append({"date":d,"open":op,"close":cl,"high":max(hs)})
        bysym[sym]=days
    return bysym

def stdev_rets(xs):
    if len(xs)<3:return None
    rs=[xs[i]/xs[i-1]-1 for i in range(1,len(xs)) if xs[i-1]]
    return statistics.pstdev(rs)*100 if rs else None

def build_rows(bysym):
    raw=[]
    max_h=max(HORIZONS)
    for sym,days in bysym.items():
        closes=[x["close"] for x in days]
        for i in range(60,len(days)-max_h-1):
            ma20=statistics.mean(closes[i-19:i+1])
            ma60=statistics.mean(closes[i-59:i+1])
            high20=max(x["high"] for x in days[i-19:i+1])
            ret20=(closes[i]/closes[i-20]-1)*100 if closes[i-20] else None
            vol20=stdev_rets(closes[i-19:i+1])
            entry=days[i+1]["open"]
            if entry is None or entry>100 or ret20 is None or vol20 is None:
                continue
            rec={
                "symbol":sym,
                "date":days[i]["date"],
                "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None,
                "vol20":vol20,
                "drawdown20":(closes[i]/high20-1)*100 if high20 else None,
                "ret20":ret20,
            }
            for h in HORIZONS:
                rec[f"raw_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)

    bydate=defaultdict(list)
    for r in raw:
        bydate[r["date"]].append(r)

    out=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if all(
            r.get(k) is not None for k in
            ("trend_ma20","trend_ma60","vol20","drawdown20","ret20")
        )]
        if len(valid)<20:
            continue
        ret20s=sorted(r["ret20"] for r in valid)
        breadth=sum(r["trend_ma20"]>0 for r in valid)/len(valid)
        for r in valid:
            r["ret20_rank"]=sum(v<=r["ret20"] for v in ret20s)/len(ret20s)
            r["market_breadth20"]=breadth
        for h in HORIZONS:
            market_mean=statistics.mean(r[f"raw_{h}d"] for r in valid)
            for r in valid:
                r[f"market_resid_{h}d"]=r[f"raw_{h}d"]-market_mean
        out.extend(valid)
    return out

def deciles(rows,feature,target):
    arr=[r for r in rows if r.get(target) is not None and r.get(feature) is not None]
    if len(arr)<100:return {}
    arr=sorted(arr,key=lambda r:r[feature]); n=len(arr); out={}
    for d in range(10):
        lo=d*n//10; hi=(d+1)*n//10
        vals=[r[target] for r in arr[lo:hi]]
        out[str(d+1)]=statistics.mean(vals) if vals else None
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_residual_label")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    rows=build_rows(load_daily(args.history_dir))
    splits={
        "train":[r for r in rows if int(r["date"][:4])<=2024],
        "validation":[r for r in rows if int(r["date"][:4])==2025],
        "research_test":[r for r in rows if int(r["date"][:4])==2026],
    }
    report={
        "method":"VNext Residual Return Label Audit v1",
        "target":"market residual only",
        "features":FEATURES,
        "horizons":HORIZONS,
        "split_counts":{k:len(v) for k,v in splits.items()},
        "results":{},
        "train_selected":{},
        "production_eligible":False,
        "fresh_oos":False,
        "limitations":[
            "Current historical sample may retain survivorship bias.",
            "2026 has been observed in prior research and is Research Test, not fresh untouched OOS.",
            "Industry residual is disabled until PIT sector mapping is verified.",
        ],
    }

    for h in HORIZONS:
        target=f"market_resid_{h}d"
        report["results"][target]={}
        selected=[]
        for feature in FEATURES:
            rr={}
            for sp,arr in splits.items():
                a=[r for r in arr if r.get(target) is not None and r.get(feature) is not None]
                ic=spearman([r[feature] for r in a],[r[target] for r in a])
                rr[sp]={"rank_ic":ic,"n":len(a),"deciles":deciles(a,feature,target)}
            train_ic=rr["train"]["rank_ic"]
            direction=1 if train_ic is not None and train_ic>0 else -1
            include=bool(train_ic is not None and abs(train_ic)>=0.02)
            rr["train_selected"]=include
            rr["train_direction"]=direction if include else None
            report["results"][target][feature]=rr
            if include:
                selected.append({"feature":feature,"direction":direction,"train_rank_ic":train_ic})
        report["train_selected"][str(h)]=selected

    (out/"residual_label_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    lines=[
        "# Sky VNext Residual Label Audit v1",
        f"- Split counts: {report['split_counts']}",
        "- 2026 role: Research Test (not fresh OOS)",
        "- Industry residual: disabled until PIT sector mapping is verified",
    ]
    for h in HORIZONS:
        lines.append(f"\n## {h}D Train-selected features")
        selected=report["train_selected"][str(h)]
        if not selected:
            lines.append("- None")
        for x in selected:
            lines.append(
                f"- {x['feature']} | direction={x['direction']} | "
                f"Train IC={x['train_rank_ic']:.4f}"
            )
    (out/"residual_label_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
