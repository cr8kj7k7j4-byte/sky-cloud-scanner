from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
import pandas as pd

HORIZONS=[5,10,20]
FEATURES=["yoy","mom","yoy_accel","cum_yoy","new_high_12m"]
COSTS=[0.20,0.45]

def fnum(x):
    try:
        if x is None:return None
        s=str(x).strip().replace(",","").replace("%","")
        if s in ("","nan","NaN","None","--","-"):return None
        return float(s)
    except Exception:return None

def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i:vals[i]);out=[0.0]*len(vals);i=0
    while i<len(order):
        j=i
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]:j+=1
        rr=(i+j)/2
        for k in range(i,j+1):out[order[k]]=rr
        i=j+1
    return out

def pearson(x,y):
    if len(x)<3:return None
    mx=statistics.mean(x);my=statistics.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx=sum((a-mx)**2 for a in x);dy=sum((b-my)**2 for b in y)
    if dx<=0 or dy<=0:return None
    return num/(dx*dy)**0.5

def spearman(x,y):return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals)}

def load_prices(history_dir):
    bysym={}
    trading=set()
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"));sym=str(o["symbol"]);by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:
                d=datetime.fromisoformat(ds).date().isoformat()
                by[d].append(b);trading.add(d)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open"));cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            days.append({"date":d,"open":op,"close":cl})
        bysym[sym]=days
    return bysym,sorted(trading)

def next_month(y,m):return (y+1,1) if m==12 else (y,m+1)

def knowledge_date(y,m,trading):
    ny,nm=next_month(y,m)
    cutoff=date(ny,nm,10).isoformat()
    for d in trading:
        if d>cutoff:return d
    return None

def prepare_revenue(csv_path):
    df=pd.read_csv(csv_path,dtype={"symbol":str})
    rows=df.to_dict("records")
    by=defaultdict(list)
    for r in rows:
        r["symbol"]=str(r["symbol"]).replace(".0","")
        r["year"]=int(r["year"]);r["month"]=int(r["month"])
        by[r["symbol"]].append(r)
    out=[]
    for sym,arr in by.items():
        arr.sort(key=lambda r:(r["year"],r["month"]))
        prev_yoy=None;hist=[]
        for r in arr:
            rev=fnum(r.get("revenue")); yoy=fnum(r.get("yoy")); mom=fnum(r.get("mom")); cum=fnum(r.get("cum_yoy"))
            lyr=fnum(r.get("last_year_revenue")); prev=fnum(r.get("prev_revenue"))
            if yoy is None and rev is not None and lyr not in (None,0):yoy=(rev/lyr-1)*100
            if mom is None and rev is not None and prev not in (None,0):mom=(rev/prev-1)*100
            accel=yoy-prev_yoy if yoy is not None and prev_yoy is not None else None
            hh=hist[-11:]+([rev] if rev is not None else [])
            nh=1.0 if rev is not None and len(hh)>=12 and rev>=max(hh) else 0.0
            out.append({**r,"revenue":rev,"yoy":yoy,"mom":mom,"cum_yoy":cum,"yoy_accel":accel,"new_high_12m":nh})
            if rev is not None:hist.append(rev)
            if yoy is not None:prev_yoy=yoy
    return out

def build_events(rev,bysym,trading):
    lookup={s:{d["date"]:i for i,d in enumerate(days)} for s,days in bysym.items()}
    ev=[]
    for r in rev:
        sym=r["symbol"]
        if sym not in bysym:continue
        kd=knowledge_date(r["year"],r["month"],trading)
        if not kd or kd not in lookup[sym]:continue
        i=lookup[sym][kd];days=bysym[sym]
        entry=days[i]["open"]
        if entry is None or entry>100:continue
        e={**r,"knowledge_date":kd,"entry":entry}
        ok=False
        for h in HORIZONS:
            j=i+h
            if j<len(days):
                e[f"ret_{h}d"]=(days[j]["close"]/entry-1)*100;ok=True
        if ok:ev.append(e)
    return ev

def quantile_pick(arr,f,target,sign,cost):
    a=[x for x in arr if x.get(f) is not None and x.get(target) is not None]
    if len(a)<20:return {"n":0}
    a=sorted(a,key=lambda x:x[f]);k=max(1,len(a)//10)
    pick=a[-k:] if sign>0 else a[:k]
    return metrics([x[target]-cost for x in pick])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--revenue-csv",required=True)
    ap.add_argument("--out",default="research_output_revenue_oos")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    bysym,trading=load_prices(args.history_dir)
    rev=prepare_revenue(args.revenue_csv)
    events=build_events(rev,bysym,trading)
    splits={"train":[e for e in events if int(e["knowledge_date"][:4])<=2024],
            "valid":[e for e in events if int(e["knowledge_date"][:4])==2025],
            "test":[e for e in events if int(e["knowledge_date"][:4])==2026]}

    report={"method":"Revenue Surprise / Acceleration OOS using governed monthly revenue evidence",
            "alignment":"Revenue month becomes usable on first sample trading day strictly after next-month day 10.",
            "features":FEATURES,"horizons":HORIZONS,"costs":COSTS,
            "event_count":len(events),"split_counts":{k:len(v) for k,v in splits.items()},
            "results":{},"stable_pairs":[],"promotion_candidates":[],
            "pre_pit_candidates":[],
            "point_in_time_verified":False,
            "promotion_blocked_reason":"Company filing timestamp not verified; statutory deadline proxy only.",
            "production_eligible":False,
            "limitations":["Current-universe survivorship bias from 100-stock price sample.","Knowledge-date uses conservative statutory deadline proxy, not company filing timestamp.","2026 has been observed in broader research and is not globally untouched OOS."]}

    for h in HORIZONS:
        target=f"ret_{h}d"
        for f in FEATURES:
            key=f"{f}_{h}d"; rr={}; signs=[];ok=True
            for sp,arr in splits.items():
                a=[e for e in arr if e.get(f) is not None and e.get(target) is not None]
                ic=spearman([e[f] for e in a],[e[target] for e in a]) if len(a)>=30 else None
                rr[sp]={"rank_ic":ic,"n":len(a)}
                if ic is None:ok=False
                else:signs.append(1 if ic>0 else -1)
            stable=ok and len(set(signs))==1 and min(abs(rr[s]["rank_ic"]) for s in ("train","valid","test"))>=0.02
            rr["stable"]=stable
            if stable:
                sign=signs[0]
                report["stable_pairs"].append({"feature":f,"horizon":h,"sign":sign})
                rr["quantiles"]={}
                for c in COSTS:
                    ck=f"{c:.2f}"
                    rr["quantiles"][ck]={sp:quantile_pick(arr,f,target,sign,c) for sp,arr in splits.items()}
                q=rr["quantiles"]["0.45"]
                if all(q[s].get("n",0)>=20 and (q[s].get("expectancy_pct") or -999)>0 and (q[s].get("pf") or 0)>1.05 for s in ("train","valid","test")):
                    report["pre_pit_candidates"].append(key)
            report["results"][key]=rr

    (out/"revenue_oos_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Revenue Surprise / Acceleration OOS Research",
           f"- Events: {report['event_count']}",
           f"- Split counts: {report['split_counts']}",
           f"- Stable pairs: {report['stable_pairs']}",
           f"- Pre-PIT candidates @0.45%: {report['pre_pit_candidates']}",
           f"- Point-in-time verified: {report['point_in_time_verified']}",
           f"- Promotion candidates: {report['promotion_candidates']}"]
    for key in report["pre_pit_candidates"]+[
        f"{x['feature']}_{x['horizon']}d" for x in report["stable_pairs"]
        if f"{x['feature']}_{x['horizon']}d" not in report["promotion_candidates"]][:15]:
        rr=report["results"][key]
        if "quantiles" in rr:
            lines.append(f"\n## {key} @0.45%")
            for sp in ("train","valid","test"):
                lines.append(f"- {sp}: IC={rr[sp]['rank_ic']} {rr['quantiles']['0.45'][sp]}")
    (out/"revenue_oos_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
