from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[5,10,15,20]
COSTS=[0.35,0.45,0.55,0.65]
FEATURES=["trend_ma20","trend_ma60","market_breadth20"]

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
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]:j+=1
        rr=(i+j)/2
        for k in range(i,j+1):out[order[k]]=rr
        i=j+1
    return out

def spearman(x,y): return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals)}

def load_daily(history_dir):
    bysym={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8")); sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            days.append({"date":d,"open":op,"close":cl})
        bysym[sym]=days
    return bysym

def build_rows(bysym):
    raw=[]
    for sym,days in bysym.items():
        closes=[d["close"] for d in days]
        for i in range(60,len(days)-21):
            ma20=statistics.mean(closes[i-19:i+1]); ma60=statistics.mean(closes[i-59:i+1])
            entry=days[i+1]["open"]
            if entry is None or entry>100:continue
            rec={"symbol":sym,"date":days[i]["date"],
                 "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                 "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None}
            for h in HORIZONS:
                rec[f"ret_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)
    bydate=defaultdict(list)
    for r in raw:bydate[r["date"]].append(r)
    rows=[]
    for d,arr in bydate.items():
        v=[r for r in arr if r["trend_ma20"] is not None and r["trend_ma60"] is not None]
        if len(v)<20:continue
        breadth=sum(r["trend_ma20"]>0 for r in v)/len(v)
        med60=statistics.median(r["trend_ma60"] for r in v)
        rg="bull" if breadth>=0.55 and med60>0 else "bear" if breadth<=0.45 and med60<0 else "neutral"
        for r in v:
            r["market_breadth20"]=breadth;r["regime"]=rg;rows.append(r)
    return rows

def zfit(rows):
    return {f:(statistics.mean([r[f] for r in rows]),statistics.pstdev([r[f] for r in rows]) or 1.0) for f in FEATURES}

def score(r,st,w): return sum(w[f]*((r[f]-st[f][0])/st[f][1]) for f in FEATURES)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_swing_stability")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]

    # freeze 5D train IC weights
    audits={}
    for f in FEATURES:
        audits[f]=spearman([r[f] for r in train],[r["ret_5d"] for r in train])
    total=sum(abs(v) for v in audits.values()) or 1.0
    w={f:(1 if audits[f]>0 else -1)*abs(audits[f])/total for f in FEATURES}
    st=zfit(train)
    q90=sorted(score(r,st,w) for r in train)[int(0.9*(len(train)-1))]

    report={"weights":w,"train_q90":q90,"horizons":{}}
    lines=["# Sky Swing Candidate Stability",f"- Weights: {w}",f"- Train q90: {q90}"]

    for h in HORIZONS:
        t=f"ret_{h}d"; node={"cost_stress":{},"yearly":{},"regime":{},"deciles":{}}
        for c in COSTS:
            ck=f"{c:.2f}";node["cost_stress"][ck]={}
            for sp,arr in (("train",train),("valid",valid),("test",test)):
                vals=[r[t]-c for r in arr if score(r,st,w)>=q90]
                node["cost_stress"][ck][sp]=metrics(vals)
        for yr in sorted(set(int(r["date"][:4]) for r in rows)):
            arr=[r for r in rows if int(r["date"][:4])==yr and score(r,st,w)>=q90]
            node["yearly"][str(yr)]=metrics([r[t]-0.45 for r in arr])
        for rg in ("bull","neutral","bear"):
            arr=[r for r in rows if r["regime"]==rg and score(r,st,w)>=q90]
            node["regime"][rg]=metrics([r[t]-0.45 for r in arr])
        for sp,arr in (("train",train),("valid",valid),("test",test)):
            ranked=sorted((score(r,st,w),r[t]-0.45) for r in arr)
            n=len(ranked); dm={}
            for d in range(10):
                vals=[v for _,v in ranked[d*n//10:(d+1)*n//10]]
                dm[str(d+1)]=statistics.mean(vals) if vals else None
            node["deciles"][sp]=dm
        report["horizons"][str(h)]=node

        lines.append(f"\n## {h}D cost stress")
        for c in COSTS:
            v=node["cost_stress"][f"{c:.2f}"]["valid"]
            t0=node["cost_stress"][f"{c:.2f}"]["test"]
            lines.append(f"- cost {c:.2f}% | valid exp={v.get('expectancy_pct')} PF={v.get('pf')} | test exp={t0.get('expectancy_pct')} PF={t0.get('pf')}")
        lines.append(f"## {h}D yearly @0.45%")
        for yr,m in node["yearly"].items():
            lines.append(f"- {yr}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')}")
        lines.append(f"## {h}D regime @0.45%")
        for rg,m in node["regime"].items():
            lines.append(f"- {rg}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')}")

    (out/"swing_candidate_stability.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"swing_candidate_stability.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
