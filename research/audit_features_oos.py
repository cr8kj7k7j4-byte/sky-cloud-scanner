from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FEATURES=["mom5","mom15","mom30","vwap_dist","range_pos","drawdown","vol_ratio","volatility","rs_rank","market_breadth"]
HORIZONS=["30m","60m","120m"]

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
    out=[0.0]*len(vals)
    i=0
    while i<len(order):
        j=i
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]: j+=1
        r=(i+j)/2
        for k in range(i,j+1):out[order[k]]=r
        i=j+1
    return out

def spearman(x,y):
    return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def quantile_bins(rows,feature,n=10):
    vals=sorted(r[feature] for r in rows if r.get(feature) is not None)
    if len(vals)<n:return {}
    cuts=[]
    for k in range(1,n):
        pos=(len(vals)-1)*k/n
        lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        if lo==hi:q=vals[lo]
        else:q=vals[lo]+(vals[hi]-vals[lo])*(pos-lo)
        cuts.append(q)
    out=defaultdict(list)
    for r in rows:
        x=r.get(feature)
        if x is None:continue
        b=sum(x>c for c in cuts)+1
        out[b].append(r)
    return out

def monotonic_score(means):
    xs=[means[k] for k in sorted(means) if means[k] is not None]
    if len(xs)<4:return None
    diffs=[xs[i+1]-xs[i] for i in range(len(xs)-1)]
    up=sum(d>0 for d in diffs)/(len(diffs))
    down=sum(d<0 for d in diffs)/(len(diffs))
    return max(up,down)

def load_feature_report(path):
    j=json.loads(Path(path).read_text(encoding="utf-8"))
    return j

def load_rows_from_history(history_dir):
    # Rebuild same feature snapshots as feature-state discovery, compactly.
    from collections import deque
    syms={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:
                by[datetime.fromisoformat(ds).date().isoformat()].append(b)
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
                if i>=len(bars) or i+25>=len(bars):continue
                c=closes[i]
                if c is None:continue
                def ret(j):
                    return (c/closes[j]-1)*100 if j>=0 and closes[j] not in (None,0) else None
                mom5=ret(i-1); mom15=ret(i-3); mom30=ret(i-6)
                cum=bars[:i+1]; den=sum((fnum(x.get("volume")) or 0) for x in cum)
                vwap=(sum((fnum(x.get("volume")) or 0)*(fnum(x.get("average")) if fnum(x.get("average")) is not None else fnum(x.get("close"))) for x in cum)/den) if den>0 else None
                vdist=(c/vwap-1)*100 if vwap else None
                hh=max(x for x in highs[:i+1] if x is not None); ll=min(x for x in lows[:i+1] if x is not None)
                rpos=(c-ll)/(hh-ll) if hh>ll else None
                draw=(c/hh-1)*100 if hh else None
                vol15=sum(vols[max(0,i-2):i+1]); hist=vol_hist[sym][i]
                vr=vol15/statistics.median(hist) if len(hist)>=lookback and statistics.median(hist)>0 else None
                rets=[]
                seg=[x for x in closes[max(0,i-5):i+1] if x is not None]
                for z in range(1,len(seg)):
                    if seg[z-1]:rets.append(seg[z]/seg[z-1]-1)
                vola=statistics.pstdev(rets)*100 if rets else None
                entry=fnum(bars[i+1].get("open"))
                if entry is None or entry>100:continue
                outs={}
                for hn,off in {"30m":6,"60m":12,"120m":24}.items():
                    px=closes[i+1+off]
                    if px is not None:outs[hn]=(px/entry-1)*100
                slotrows[i].append({"symbol":sym,"date":d,"slot":i,"mom5":mom5,"mom15":mom15,"mom30":mom30,
                                    "vwap_dist":vdist,"range_pos":rpos,"drawdown":draw,"vol_ratio":vr,"volatility":vola,**outs})
        for i,arr in slotrows.items():
            e=[r for r in arr if all(r.get(k) is not None for k in ("mom15","vwap_dist","range_pos","vol_ratio","volatility"))]
            if len(e)>=20:
                vals=sorted(r["mom15"] for r in e)
                breadth=sum(r["mom15"]>0 for r in e)/len(e)
                for r in e:
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_feature_audit")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=load_rows_from_history(args.history_dir)
    for r in rows:
        y=int(r["date"][:4])
        r["split"]="train" if y<=2024 else "valid" if y==2025 else "test"
        r["year"]=y
        r["time_bucket"]="early" if r["slot"]<=9 else "mid" if r["slot"]<=21 else "late"
        r["regime"]="bullish_intraday" if r["market_breadth"]>=0.6 else "bearish_intraday" if r["market_breadth"]<=0.4 else "neutral_intraday"

    report={"eligible_rows":len(rows),"features":{}}
    for f in FEATURES:
        fr={}
        for h in HORIZONS:
            hr={}
            for sp in ("train","valid","test"):
                arr=[r for r in rows if r["split"]==sp and r.get(f) is not None and r.get(h) is not None]
                x=[r[f] for r in arr]; y=[r[h] for r in arr]
                bins=quantile_bins(arr,f,10)
                means={b:(statistics.mean([r[h] for r in rr])-0.20 if rr else None) for b,rr in bins.items()}
                hr[sp]={"n":len(arr),"ic":pearson(x,y),"rank_ic":spearman(x,y),"decile_net_means_pct":means,
                        "monotonic_score":monotonic_score(means)}
            # stability by year/regime/time
            yearly={}; regimes={}; times={}
            for yr in sorted(set(r["year"] for r in rows)):
                arr=[r for r in rows if r["year"]==yr and r.get(f) is not None and r.get(h) is not None]
                if len(arr)>=200:yearly[str(yr)]={"n":len(arr),"rank_ic":spearman([r[f] for r in arr],[r[h] for r in arr])}
            for rg in ("bullish_intraday","neutral_intraday","bearish_intraday"):
                arr=[r for r in rows if r["regime"]==rg and r.get(f) is not None and r.get(h) is not None]
                if len(arr)>=200:regimes[rg]={"n":len(arr),"rank_ic":spearman([r[f] for r in arr],[r[h] for r in arr])}
            for tb in ("early","mid","late"):
                arr=[r for r in rows if r["time_bucket"]==tb and r.get(f) is not None and r.get(h) is not None]
                if len(arr)>=200:times[tb]={"n":len(arr),"rank_ic":spearman([r[f] for r in arr],[r[h] for r in arr])}
            hr["yearly"]=yearly;hr["regimes"]=regimes;hr["time_buckets"]=times
            # audit pass requires same IC direction in train/valid/test and useful magnitude
            vals=[hr[s]["rank_ic"] for s in ("train","valid","test")]
            same=all(v is not None and v>0 for v in vals) or all(v is not None and v<0 for v in vals)
            hr["audit_pass"]=bool(same and min(abs(v) for v in vals)>=0.02)
            fr[h]=hr
        report["features"][f]=fr

    passed=[]
    for f,fr in report["features"].items():
        for h,hr in fr.items():
            if hr["audit_pass"]:
                passed.append({"feature":f,"horizon":h,
                               "train_rank_ic":hr["train"]["rank_ic"],
                               "valid_rank_ic":hr["valid"]["rank_ic"],
                               "test_rank_ic":hr["test"]["rank_ic"]})
    report["passed_feature_horizons"]=passed
    report["production_eligible"]=False
    report["note"]="Feature audit only; passing features may enter P0-ML research, not production."
    (out/"feature_audit_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky P0-F Feature Audit",f"- Eligible rows: {len(rows)}",f"- Passed feature-horizons: {len(passed)}"]
    for x in passed[:20]:
        lines.append(f"- {x['feature']} / {x['horizon']}: Train {x['train_rank_ic']:.4f}, Valid {x['valid_rank_ic']:.4f}, Test {x['test_rank_ic']:.4f}")
    if not passed:lines.append("- No feature-horizon passed the stability gate.")
    (out/"feature_audit_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
