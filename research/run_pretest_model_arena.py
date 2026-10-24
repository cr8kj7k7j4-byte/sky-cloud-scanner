from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path

HORIZON="60m"
FEATURES=["vwap_dist","drawdown","volatility","rs_rank","market_breadth"]
COST=0.20

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

def load_rows(history_dir):
    syms={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds: by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        for d in by:by[d].sort(key=lambda x:x["date"])
        syms[sym]=by

    slots=range(3,37,3); lookback=20
    vol_hist=defaultdict(lambda:defaultdict(lambda:deque(maxlen=lookback)))
    rows=[]; dates=sorted({d for by in syms.values() for d in by})
    for d in dates:
        slotrows=defaultdict(list)
        for sym,by in syms.items():
            bars=by.get(d)
            if not bars or len(bars)<30:continue
            closes=[fnum(b.get("close")) for b in bars]
            highs=[fnum(b.get("high")) for b in bars]
            lows=[fnum(b.get("low")) for b in bars]
            vols=[fnum(b.get("volume")) or 0 for b in bars]
            for i in slots:
                if i>=len(bars) or i+13>=len(bars):continue
                c=closes[i]
                if c is None:continue
                cum=bars[:i+1]; den=sum((fnum(x.get("volume")) or 0) for x in cum)
                vwap=(sum((fnum(x.get("volume")) or 0)*(fnum(x.get("average")) if fnum(x.get("average")) is not None else fnum(x.get("close"))) for x in cum)/den) if den>0 else None
                vdist=(c/vwap-1)*100 if vwap else None
                hh=max(x for x in highs[:i+1] if x is not None); ll=min(x for x in lows[:i+1] if x is not None)
                draw=(c/hh-1)*100 if hh else None
                vol15=sum(vols[max(0,i-2):i+1]); hist=vol_hist[sym][i]
                vr=vol15/statistics.median(hist) if len(hist)>=lookback and statistics.median(hist)>0 else None
                seg=[x for x in closes[max(0,i-5):i+1] if x is not None]
                rets=[seg[z]/seg[z-1]-1 for z in range(1,len(seg)) if seg[z-1]]
                vola=statistics.pstdev(rets)*100 if rets else None
                entry=fnum(bars[i+1].get("open"))
                px=closes[i+13]
                if entry is None or px is None or entry>100:continue
                slotrows[i].append({"symbol":sym,"date":d,"slot":i,"vwap_dist":vdist,"drawdown":draw,
                                    "volatility":vola,"vol_ratio":vr,"target60":(px/entry-1)*100})
        for i,arr in slotrows.items():
            e=[r for r in arr if all(r.get(k) is not None for k in ("vwap_dist","drawdown","volatility"))]
            if len(e)>=20:
                # RS rank based on 15m momentum from source bars, reconstructed here
                moms=[]
                valid=[]
                for r in e:
                    b=syms[r["symbol"]][d]; c=fnum(b[i].get("close")); p=fnum(b[i-3].get("close")) if i>=3 else None
                    if c is None or p in (None,0): continue
                    r["mom15"]=(c/p-1)*100; moms.append(r["mom15"]); valid.append(r)
                if len(valid)<20:continue
                vals=sorted(moms); breadth=sum(v>0 for v in moms)/len(moms)
                for r in valid:
                    r["rs_rank"]=sum(v<=r["mom15"] for v in vals)/len(vals)
                    r["market_breadth"]=breadth
                    rows.append(r)
        for sym,by in syms.items():
            bars=by.get(d)
            if not bars:continue
            vols=[fnum(b.get("volume")) or 0 for b in bars]
            for i in slots:
                if i<len(bars):vol_hist[sym][i].append(sum(vols[max(0,i-2):i+1]))
    return rows

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,"win_rate":sum(v>0 for v in vals)/len(vals)}

def zfit(rows,features):
    stats={}
    for f in features:
        xs=[r[f] for r in rows]
        m=statistics.mean(xs); s=statistics.pstdev(xs) or 1.0
        stats[f]=(m,s)
    return stats

def score_row(r,stats,weights):
    return sum(weights[f]*((r[f]-stats[f][0])/stats[f][1]) for f in weights)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_ml_arena")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=load_rows(args.history_dir)
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]

    # Feature selection uses TRAIN + VALIDATION ONLY. 2026 is untouched until final evaluation.
    selected=[]
    direction={}
    audit={}
    for f in FEATURES:
        ti=spearman([r[f] for r in train],[r["target60"] for r in train])
        vi=spearman([r[f] for r in valid],[r["target60"] for r in valid])
        same=(ti is not None and vi is not None and ((ti>0 and vi>0) or (ti<0 and vi<0)))
        keep=bool(same and min(abs(ti),abs(vi))>=0.02)
        audit[f]={"train_rank_ic":ti,"valid_rank_ic":vi,"selected_pretest":keep}
        if keep:
            selected.append(f);direction[f]=1.0 if ti>0 else -1.0

    # Transparent linear ensemble, weights proportional to TRAIN |Rank IC| only.
    if selected:
        total=sum(abs(audit[f]["train_rank_ic"]) for f in selected)
        weights={f:direction[f]*abs(audit[f]["train_rank_ic"])/total for f in selected}
    else:weights={}
    stats=zfit(train,selected) if selected else {}

    def eval_split(arr,name):
        if not selected:return {"name":name,"n":0}
        scored=[(score_row(r,stats,weights),r) for r in arr]
        scored.sort(key=lambda x:x[0],reverse=True)
        # trade top decile only; threshold is TRAIN score 90th percentile and frozen
        return scored

    train_scored=eval_split(train,"train")
    train_scores=sorted(s for s,_ in train_scored)
    q90=train_scores[max(0,int(0.90*(len(train_scores)-1)))] if train_scores else None

    result={}
    for name,arr in (("train",train),("valid",valid),("test",test)):
        scored=eval_split(arr,name)
        chosen=[r["target60"]-COST for s,r in scored if q90 is not None and s>=q90]
        result[name]=metrics(chosen)

    promo=(result["valid"].get("n",0)>=300 and result["test"].get("n",0)>=300 and
           (result["valid"].get("expectancy_pct") or -999)>0 and (result["test"].get("expectancy_pct") or -999)>0 and
           (result["valid"].get("pf") or 0)>1.05 and (result["test"].get("pf") or 0)>1.05)

    report={"method":"P0-ML transparent linear feature ensemble, pretest selection only",
            "target":"future 60m return from next 5m bar open",
            "cost_pct":COST,
            "feature_selection":"2023-24 train + 2025 validation only; 2026 untouched until final test",
            "candidate_features":FEATURES,"selected_features":selected,"audit":audit,
            "weights":weights,"train_score_q90":q90,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},
            "results":result,"promotion_pass":promo,
            "production_eligible":False,
            "note":"Even if statistical gate passes, paper trading and cost/slippage stress remain required before production."}
    (out/"pretest_model_arena_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky P0-ML Pretest Model Arena",f"- Selected features: {selected}",f"- Promotion pass: **{promo}**"]
    for sp in ("train","valid","test"):
        m=result[sp];lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"pretest_model_arena_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
