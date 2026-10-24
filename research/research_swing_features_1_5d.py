from __future__ import annotations
import argparse,json,statistics,math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[1,2,3,5]
COSTS=[0.20,0.35,0.45,0.55]
FEATURES=["drawdown20","vol20","rs20_rank","trend_ma20","trend_ma60","vol_ratio20","market_breadth20"]

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
        for k in range(i,j+1):out[order[k]]=r
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

def load_daily(history_dir):
    bysym={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8")); sym=str(o["symbol"])
        by=defaultdict(list)
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

def stdev_rets(closes):
    if len(closes)<3:return None
    rs=[closes[i]/closes[i-1]-1 for i in range(1,len(closes)) if closes[i-1]]
    return statistics.pstdev(rs)*100 if rs else None

def build_rows(bysym):
    raw=[]
    for sym,days in bysym.items():
        for i in range(60,len(days)-6):
            d=days[i]
            closes=[x["close"] for x in days]
            vols=[x["volume"] for x in days]
            ma20=statistics.mean(closes[i-19:i+1])
            ma60=statistics.mean(closes[i-59:i+1])
            high20=max(x["high"] for x in days[i-19:i+1])
            draw=(d["close"]/high20-1)*100
            vol20=stdev_rets(closes[i-19:i+1])
            ret20=(d["close"]/closes[i-20]-1)*100 if closes[i-20] else None
            volbase=statistics.mean(vols[i-20:i])
            vr=d["volume"]/volbase if volbase>0 else None
            trend20=(d["close"]/ma20-1)*100 if ma20 else None
            trend60=(d["close"]/ma60-1)*100 if ma60 else None
            entry=days[i+1]["open"]
            if entry is None or entry>100:continue
            targets={}
            for h in HORIZONS:
                px=days[i+h]["close"]
                targets[f"ret_{h}d"]=(px/entry-1)*100 if px is not None else None
            raw.append({"symbol":sym,"date":d["date"],"drawdown20":draw,"vol20":vol20,
                        "ret20":ret20,"trend_ma20":trend20,"trend_ma60":trend60,
                        "vol_ratio20":vr,**targets})
    bydate=defaultdict(list)
    for r in raw:bydate[r["date"]].append(r)
    rows=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if all(r.get(k) is not None for k in ("ret20","drawdown20","vol20","trend_ma20","trend_ma60","vol_ratio20"))]
        if len(valid)<20:continue
        vals=sorted(r["ret20"] for r in valid)
        breadth=sum(r["trend_ma20"]>0 for r in valid)/len(valid)
        for r in valid:
            r["rs20_rank"]=sum(v<=r["ret20"] for v in vals)/len(vals)
            r["market_breadth20"]=breadth
            rows.append(r)
    return rows

def zfit(rows,features):
    out={}
    for f in features:
        xs=[r[f] for r in rows]
        out[f]=(statistics.mean(xs),statistics.pstdev(xs) or 1.0)
    return out

def score(r,stats,weights):
    return sum(weights[f]*((r[f]-stats[f][0])/stats[f][1]) for f in weights)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_swing_features")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]

    audit={}
    selected_by_h={}
    for h in HORIZONS:
        target=f"ret_{h}d"; audit[str(h)]={}
        selected=[]
        for f in FEATURES:
            ta=[r for r in train if r.get(target) is not None]
            va=[r for r in valid if r.get(target) is not None]
            ti=spearman([r[f] for r in ta],[r[target] for r in ta])
            vi=spearman([r[f] for r in va],[r[target] for r in va])
            same=ti is not None and vi is not None and ((ti>0 and vi>0) or (ti<0 and vi<0))
            keep=bool(same and min(abs(ti),abs(vi))>=0.02)
            audit[str(h)][f]={"train_rank_ic":ti,"valid_rank_ic":vi,"selected":keep}
            if keep:selected.append(f)
        selected_by_h[str(h)]=selected

    models={}
    for h in HORIZONS:
        target=f"ret_{h}d"; feats=selected_by_h[str(h)]
        models[str(h)]={"selected_features":feats,"costs":{}}
        if not feats:continue
        total=sum(abs(audit[str(h)][f]["train_rank_ic"]) for f in feats) or 1.0
        weights={f:(1 if audit[str(h)][f]["train_rank_ic"]>0 else -1)*abs(audit[str(h)][f]["train_rank_ic"])/total for f in feats}
        stats=zfit(train,feats)
        tr_scores=sorted(score(r,stats,weights) for r in train)
        q90=tr_scores[int(0.90*(len(tr_scores)-1))]
        models[str(h)]["weights"]=weights;models[str(h)]["q90"]=q90
        for c in COSTS:
            ck=f"{c:.2f}";models[str(h)]["costs"][ck]={}
            for sp,arr in (("train",train),("valid",valid),("test",test)):
                chosen=[r[target]-c for r in arr if r.get(target) is not None and score(r,stats,weights)>=q90]
                models[str(h)]["costs"][ck][sp]=metrics(chosen)

    candidates=[]
    for h in HORIZONS:
        m=models[str(h)]
        if "costs" not in m or "0.45" not in m["costs"]:continue
        v=m["costs"]["0.45"]["valid"];t=m["costs"]["0.45"]["test"]
        if v.get("n",0)>=200 and t.get("n",0)>=200 and (v.get("expectancy_pct") or -999)>0 and (t.get("expectancy_pct") or -999)>0 and (v.get("pf") or 0)>1.05 and (t.get("pf") or 0)>1.05:
            candidates.append(h)
    report={"method":"Sky Swing 1-5D transparent feature model",
            "features":FEATURES,"horizons_days":HORIZONS,"costs_pct":COSTS,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},
            "audit":audit,"models":models,"promotion_candidates_at_0.45":candidates,
            "production_eligible":False,
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","2026 has been observed in prior research; results are research evidence, not fresh untouched promotion."]}
    (out/"swing_feature_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Swing 1-5D Feature Research",f"- Split counts: {report['split_counts']}",f"- Promotion candidates @0.45%: {candidates}"]
    for h in HORIZONS:
        lines.append(f"\n## {h}D @0.45%")
        lines.append(f"- selected: {selected_by_h[str(h)]}")
        m=models[str(h)]
        if "0.45" in m.get("costs",{}):
            for sp in ("train","valid","test"):
                x=m["costs"]["0.45"][sp]
                lines.append(f"- {sp}: n={x.get('n')} exp={x.get('expectancy_pct')} PF={x.get('pf')} win={x.get('win_rate')}")
    (out/"swing_feature_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
