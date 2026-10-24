from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path

FEATURES=["drawdown","volatility","rs_rank","market_breadth"]
COSTS=[0.00,0.05,0.10,0.15,0.20,0.25,0.35]
HORIZONS=["60m","120m","eod","next_close"]

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def pearson(x,y):
    if len(x)<3:return None
    mx=statistics.mean(x); my=statistics.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx=sum((a-mx)**2 for a in x); dy=sum((b-my)**2 for b in y)
    if dx<=0 or dy<=0:return None
    return num/(dx*dy)**0.5

def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i:vals[i])
    out=[0.0]*len(vals); i=0
    while i<len(order):
        j=i
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]: j+=1
        r=(i+j)/2
        for k in range(i,j+1): out[order[k]]=r
        i=j+1
    return out

def spearman(x,y):
    return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals)}

def load_rows(history_dir):
    syms={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds: by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        for d in by: by[d].sort(key=lambda x:x["date"])
        syms[sym]=by

    slots=range(3,37,3)
    rows=[]
    dates=sorted({d for by in syms.values() for d in by})
    next_date={}
    for sym,by in syms.items():
        ds=sorted(by)
        for i,d in enumerate(ds[:-1]): next_date[(sym,d)]=ds[i+1]

    for d in dates:
        slotrows=defaultdict(list)
        for sym,by in syms.items():
            bars=by.get(d)
            if not bars or len(bars)<30: continue
            closes=[fnum(b.get("close")) for b in bars]
            highs=[fnum(b.get("high")) for b in bars]
            for i in slots:
                if i>=len(bars) or i+13>=len(bars): continue
                c=closes[i]
                if c is None: continue
                hh=max(x for x in highs[:i+1] if x is not None)
                draw=(c/hh-1)*100 if hh else None
                seg=[x for x in closes[max(0,i-5):i+1] if x is not None]
                rets=[seg[z]/seg[z-1]-1 for z in range(1,len(seg)) if seg[z-1]]
                vola=statistics.pstdev(rets)*100 if rets else None
                entry=fnum(bars[i+1].get("open"))
                if entry is None or entry>100: continue
                px60=closes[i+13] if i+13<len(closes) else None
                px120=closes[i+25] if i+25<len(closes) else None
                pxeod=closes[-1]
                nd=next_date.get((sym,d)); pxnext=None
                if nd and by.get(nd): pxnext=fnum(by[nd][-1].get("close"))
                slotrows[i].append({
                    "symbol":sym,"date":d,"slot":i,"entry":entry,
                    "drawdown":draw,"volatility":vola,
                    "60m":(px60/entry-1)*100 if px60 is not None else None,
                    "120m":(px120/entry-1)*100 if px120 is not None else None,
                    "eod":(pxeod/entry-1)*100 if pxeod is not None else None,
                    "next_close":(pxnext/entry-1)*100 if pxnext is not None else None,
                })
        for i,arr in slotrows.items():
            valid=[]
            moms=[]
            for r in arr:
                b=syms[r["symbol"]][d]
                c=fnum(b[i].get("close")); p=fnum(b[i-3].get("close")) if i>=3 else None
                if c is None or p in (None,0) or r["drawdown"] is None or r["volatility"] is None: continue
                r["mom15"]=(c/p-1)*100
                moms.append(r["mom15"]); valid.append(r)
            if len(valid)<20: continue
            vals=sorted(moms); breadth=sum(v>0 for v in moms)/len(moms)
            for r in valid:
                r["rs_rank"]=sum(v<=r["mom15"] for v in vals)/len(vals)
                r["market_breadth"]=breadth
                rows.append(r)
    return rows

def zfit(rows):
    stats={}
    for f in FEATURES:
        xs=[r[f] for r in rows]
        m=statistics.mean(xs); s=statistics.pstdev(xs) or 1.0
        stats[f]=(m,s)
    return stats

def score(r,stats,weights):
    return sum(weights[f]*((r[f]-stats[f][0])/stats[f][1]) for f in FEATURES)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_half_life")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    rows=load_rows(args.history_dir)
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]

    # Freeze directions and weights from TRAIN only, mirroring prior research intent.
    # drawdown +, volatility -, rs_rank -, market_breadth +
    direction={"drawdown":1.0,"volatility":-1.0,"rs_rank":-1.0,"market_breadth":1.0}
    ic={}
    raw=[]
    for f in FEATURES:
        v=spearman([r[f] for r in train],[r["60m"] for r in train if r["60m"] is not None])
        # safer recomputation with aligned rows
        arr=[r for r in train if r.get("60m") is not None]
        v=spearman([r[f] for r in arr],[r["60m"] for r in arr])
        ic[f]=v
        raw.append((f,abs(v) if v is not None else 0))
    total=sum(v for _,v in raw) or 1.0
    weights={f:direction[f]*abs(ic[f])/total for f in FEATURES}
    stats=zfit(train)

    train_scores=sorted(score(r,stats,weights) for r in train)
    q90=train_scores[int(0.90*(len(train_scores)-1))]

    report={"method":"Feature half-life and transaction-cost frontier diagnostic",
            "features":FEATURES,"weights":weights,"train_q90":q90,
            "costs_pct":COSTS,"horizons":HORIZONS,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},
            "results":{},"rank_ic_by_horizon":{},"promotion_eligible":False,
            "note":"Diagnostic only. 2026 has been observed in prior research and is not treated as a fresh untouched promotion set."}

    for sp,arr in (("train",train),("valid",valid),("test",test)):
        chosen=[r for r in arr if score(r,stats,weights)>=q90]
        report["results"][sp]={}
        report["rank_ic_by_horizon"][sp]={}
        for h in HORIZONS:
            hs=[r for r in arr if r.get(h) is not None]
            report["rank_ic_by_horizon"][sp][h]=spearman([score(r,stats,weights) for r in hs],[r[h] for r in hs])
            report["results"][sp][h]={}
            for c in COSTS:
                vals=[r[h]-c for r in chosen if r.get(h) is not None]
                report["results"][sp][h][f"{c:.2f}"]=metrics(vals)

    (out/"feature_half_life_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Feature Half-Life & Cost Frontier",f"- Weights: {weights}",f"- Train q90: {q90:.6f}"]
    for h in HORIZONS:
        lines.append(f"\n## {h} @0.20%")
        for sp in ("train","valid","test"):
            m=report["results"][sp][h]["0.20"]
            ric=report["rank_ic_by_horizon"][sp][h]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')} RankIC={ric}")
    (out/"feature_half_life_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__": main()
