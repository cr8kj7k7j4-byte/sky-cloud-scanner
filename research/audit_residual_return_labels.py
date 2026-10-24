from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[1,3,5,10,15]
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

def spearman(x,y): return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def load_industry(path):
    o=json.loads(Path(path).read_text(encoding="utf-8"))
    # support either mapping or list-ish structures
    if isinstance(o,dict):
        if "data" in o and isinstance(o["data"],list):
            out={}
            for r in o["data"]:
                s=str(r.get("symbol") or r.get("code") or "")
                g=str(r.get("industry_code") or r.get("industry") or r.get("category") or "")
                if s and g: out[s]=g
            return out
        out={}
        for k,v in o.items():
            if isinstance(v,(str,int,float)): out[str(k)]=str(v)
            elif isinstance(v,dict):
                g=v.get("industry_code") or v.get("industry") or v.get("category")
                if g is not None: out[str(k)]=str(g)
        return out
    return {}

def load_daily(history_dir,industry_map):
    bysym={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8")); sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds: by[datetime.fromisoformat(ds).date().isoformat()].append(b)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open"));cl=fnum(bars[-1].get("close"))
            hs=[fnum(x.get("high")) for x in bars if fnum(x.get("high")) is not None]
            if op is None or cl is None or not hs: continue
            days.append({"date":d,"open":op,"close":cl,"high":max(hs)})
        bysym[sym]={"industry":industry_map.get(sym,"UNKNOWN"),"days":days}
    return bysym

def stdev_rets(xs):
    if len(xs)<3:return None
    rs=[xs[i]/xs[i-1]-1 for i in range(1,len(xs)) if xs[i-1]]
    return statistics.pstdev(rs)*100 if rs else None

def build_rows(bysym):
    raw=[]
    for sym,obj in bysym.items():
        days=obj["days"]; closes=[x["close"] for x in days]
        for i in range(60,len(days)-16):
            ma20=statistics.mean(closes[i-19:i+1]);ma60=statistics.mean(closes[i-59:i+1])
            high20=max(x["high"] for x in days[i-19:i+1])
            ret20=(closes[i]/closes[i-20]-1)*100 if closes[i-20] else None
            vol20=stdev_rets(closes[i-19:i+1])
            entry=days[i+1]["open"]
            if entry is None or entry>100 or ret20 is None or vol20 is None: continue
            rec={"symbol":sym,"industry":obj["industry"],"date":days[i]["date"],
                 "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                 "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None,
                 "vol20":vol20,
                 "drawdown20":(closes[i]/high20-1)*100 if high20 else None,
                 "ret20":ret20}
            for h in HORIZONS:
                rec[f"raw_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)
    bydate=defaultdict(list)
    for r in raw: bydate[r["date"]].append(r)
    out=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if all(r.get(k) is not None for k in ("trend_ma20","trend_ma60","vol20","drawdown20","ret20"))]
        if len(valid)<20: continue
        ret20s=sorted(r["ret20"] for r in valid)
        breadth=sum(r["trend_ma20"]>0 for r in valid)/len(valid)
        for r in valid:
            r["ret20_rank"]=sum(v<=r["ret20"] for v in ret20s)/len(ret20s)
            r["market_breadth20"]=breadth
        for h in HORIZONS:
            mk=[r[f"raw_{h}d"] for r in valid]
            market_mean=statistics.mean(mk)
            groups=defaultdict(list)
            for r in valid:
                if r["industry"]!="UNKNOWN": groups[r["industry"]].append(r[f"raw_{h}d"])
            group_mean={g:statistics.mean(v) for g,v in groups.items() if len(v)>=3}
            for r in valid:
                r[f"market_resid_{h}d"]=r[f"raw_{h}d"]-market_mean
                gm=group_mean.get(r["industry"])
                r[f"industry_resid_{h}d"]=r[f"raw_{h}d"]-gm if gm is not None else None
        out.extend(valid)
    return out

def deciles(rows,feature,target):
    arr=[r for r in rows if r.get(target) is not None and r.get(feature) is not None]
    if len(arr)<100:return {}
    arr=sorted(arr,key=lambda r:r[feature]);n=len(arr);out={}
    for d in range(10):
        lo=d*n//10;hi=(d+1)*n//10
        vals=[r[target] for r in arr[lo:hi]]
        out[str(d+1)]=statistics.mean(vals) if vals else None
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--industry-map",required=True)
    ap.add_argument("--out",default="research_output_residual_label")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir,load_industry(args.industry_map)))
    splits={"train":[r for r in rows if int(r["date"][:4])<=2024],
            "valid":[r for r in rows if int(r["date"][:4])==2025],
            "test":[r for r in rows if int(r["date"][:4])==2026]}
    report={"method":"Residual Return / Market-Neutral Label Audit",
            "features":FEATURES,"horizons":HORIZONS,
            "split_counts":{k:len(v) for k,v in splits.items()},
            "results":{},"stable":[],
            "production_eligible":False,
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","2026 previously observed in prior research; not globally untouched OOS."]}
    for target_type in ("raw","market_resid","industry_resid"):
      for h in HORIZONS:
        t=f"{target_type}_{h}d"; key=f"{target_type}_{h}d"
        report["results"][key]={}
        for f in FEATURES:
            rr={}; ok=True; signs=[]
            for sp,arr in splits.items():
                a=[r for r in arr if r.get(t) is not None and r.get(f) is not None]
                ic=spearman([r[f] for r in a],[r[t] for r in a])
                rr[sp]={"rank_ic":ic,"n":len(a),"deciles":deciles(a,f,t)}
                if ic is None: ok=False
                else: signs.append(1 if ic>0 else -1)
            stable=ok and len(set(signs))==1 and min(abs(rr[s]["rank_ic"]) for s in ("train","valid","test"))>=0.02
            rr["stable"]=stable
            report["results"][key][f]=rr
            if stable: report["stable"].append({"target":key,"feature":f,"sign":signs[0]})
    (out/"residual_label_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Residual Return / Market-Neutral Label Audit",
           f"- Split counts: {report['split_counts']}",
           f"- Stable feature-target pairs: {len(report['stable'])}"]
    for x in report["stable"][:50]:
        r=report["results"][x["target"]][x["feature"]]
        lines.append(f"- {x['target']} | {x['feature']} | Train {r['train']['rank_ic']:.4f} | Valid {r['valid']['rank_ic']:.4f} | Test {r['test']['rank_ic']:.4f}")
    (out/"residual_label_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":main()
