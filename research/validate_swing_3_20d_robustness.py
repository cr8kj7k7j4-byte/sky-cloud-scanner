from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[3,5,10,15,20]
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
        r=(i+j)/2
        for k in range(i,j+1):out[order[k]]=r
        i=j+1
    return out

def spearman(x,y): return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

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
        o=json.loads(p.read_text(encoding="utf-8")); sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            hs=[fnum(x.get("high")) for x in bars if fnum(x.get("high")) is not None]
            ls=[fnum(x.get("low")) for x in bars if fnum(x.get("low")) is not None]
            vol=sum((fnum(x.get("volume")) or 0) for x in bars)
            if op is None or cl is None or not hs or not ls:continue
            days.append({"date":d,"open":op,"high":max(hs),"low":min(ls),"close":cl,"volume":vol})
        bysym[sym]=days
    return bysym

def build_rows(bysym):
    raw=[]
    for sym,days in bysym.items():
        closes=[x["close"] for x in days]
        for i in range(60,len(days)-21):
            d=days[i]
            ma20=statistics.mean(closes[i-19:i+1]); ma60=statistics.mean(closes[i-59:i+1])
            ret20=(closes[i]/closes[i-20]-1)*100 if closes[i-20] else None
            entry=days[i+1]["open"]
            if entry is None or entry>100 or ret20 is None:continue
            rec={"symbol":sym,"date":d["date"],
                 "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                 "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None,
                 "ret20":ret20}
            for h in HORIZONS:
                rec[f"ret_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)
    bydate=defaultdict(list)
    for r in raw:bydate[r["date"]].append(r)
    rows=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if r["trend_ma20"] is not None and r["trend_ma60"] is not None]
        if len(valid)<20:continue
        breadth=sum(r["trend_ma20"]>0 for r in valid)/len(valid)
        med60=statistics.median(r["trend_ma60"] for r in valid)
        regime="bull" if breadth>=0.55 and med60>0 else "bear" if breadth<=0.45 and med60<0 else "neutral"
        for r in valid:
            r["market_breadth20"]=breadth;r["regime"]=regime;rows.append(r)
    return rows

def zfit(rows):
    st={}
    for f in FEATURES:
        xs=[r[f] for r in rows]
        st[f]=(statistics.mean(xs),statistics.pstdev(xs) or 1.0)
    return st

def score(r,st,w): return sum(w[f]*((r[f]-st[f][0])/st[f][1]) for f in FEATURES)

def decile_means(arr,target,st,w,cost):
    scored=sorted((score(r,st,w),r[target]-cost) for r in arr if r.get(target) is not None)
    if len(scored)<100:return {}
    out={}
    n=len(scored)
    for d in range(10):
        lo=d*n//10; hi=(d+1)*n//10
        vals=[v for _,v in scored[lo:hi]]
        out[str(d+1)]=statistics.mean(vals) if vals else None
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_swing_robust")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]

    # Freeze weights from TRAIN IC on 5D only, because 5D was the predeclared promising horizon from prior stage.
    target="ret_5d"; audits={}
    for f in FEATURES:
        ti=spearman([r[f] for r in train],[r[target] for r in train])
        vi=spearman([r[f] for r in valid],[r[target] for r in valid])
        audits[f]={"train_rank_ic_5d":ti,"valid_rank_ic_5d":vi}
    total=sum(abs(audits[f]["train_rank_ic_5d"]) for f in FEATURES) or 1.0
    w={f:(1 if audits[f]["train_rank_ic_5d"]>0 else -1)*abs(audits[f]["train_rank_ic_5d"])/total for f in FEATURES}
    st=zfit(train)
    train_scores=sorted(score(r,st,w) for r in train)
    q90=train_scores[int(0.90*(len(train_scores)-1))]

    report={"method":"Sky Swing 3-20D robustness extension","features":FEATURES,"weights":w,"train_q90":q90,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},"horizons":HORIZONS,"costs":COSTS,
            "audit":audits,"results":{},"yearly":{},"regime":{},"deciles":{},"promotion_candidate":False,
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","2026 has been observed previously; not a fresh untouched OOS."]}

    for h in HORIZONS:
        t=f"ret_{h}d";report["results"][str(h)]={}
        for c in COSTS:
            ck=f"{c:.2f}";report["results"][str(h)][ck]={}
            for sp,arr in (("train",train),("valid",valid),("test",test)):
                vals=[r[t]-c for r in arr if score(r,st,w)>=q90]
                report["results"][str(h)][ck][sp]=metrics(vals)
        report["deciles"][str(h)]={
            "train":decile_means(train,t,st,w,0.45),
            "valid":decile_means(valid,t,st,w,0.45),
            "test":decile_means(test,t,st,w,0.45)}
        report["yearly"][str(h)]={}
        for yr in sorted(set(int(r["date"][:4]) for r in rows)):
            arr=[r for r in rows if int(r["date"][:4])==yr and score(r,st,w)>=q90]
            report["yearly"][str(h)][str(yr)]=metrics([r[t]-0.45 for r in arr])
        report["regime"][str(h)]={}
        for rg in ("bull","neutral","bear"):
            arr=[r for r in rows if r["regime"]==rg and score(r,st,w)>=q90]
            report["regime"][str(h)][rg]=metrics([r[t]-0.45 for r in arr])

    m5=report["results"]["5"]["0.45"]
    report["promotion_candidate"]=bool(
        m5["train"].get("n",0)>=300 and m5["valid"].get("n",0)>=300 and m5["test"].get("n",0)>=300 and
        all((m5[s].get("expectancy_pct") or -999)>0 and (m5[s].get("pf") or 0)>1.05 for s in ("train","valid","test"))
    )
    (out/"swing_robustness_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Swing 3-20D Robustness",f"- Weights: {w}",f"- 5D promotion candidate: **{report['promotion_candidate']}**"]
    for h in HORIZONS:
        lines.append(f"\n## {h}D @0.45%")
        for sp in ("train","valid","test"):
            m=report["results"][str(h)]["0.45"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"swing_robustness_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
