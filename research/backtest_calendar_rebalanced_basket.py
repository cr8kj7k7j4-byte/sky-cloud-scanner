from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HOLDINGS=[10,15,20]
REBALANCE_DAYS=[5,10]
COSTS=[0.45,0.65]
FEATURES=["trend_ma20","trend_ma60","market_breadth20"]
WEIGHTS={"trend_ma20":-0.40057899619646997,"trend_ma60":-0.2106838328193073,"market_breadth20":-0.3887371709842227}

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
            "win_rate":sum(v>0 for v in vals)/len(vals)}

def load_daily(history_dir):
    bysym={}
    dates=set()
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8")); sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:
                d=datetime.fromisoformat(ds).date().isoformat()
                by[d].append(b);dates.add(d)
        days={}
        for d,bars in by.items():
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            days[d]={"open":op,"close":cl}
        bysym[sym]=days
    return bysym,sorted(dates)

def build_features(bysym,dates):
    idx={d:i for i,d in enumerate(dates)}
    rows=[]
    for sym,by in bysym.items():
        ds=sorted(by)
        closes=[by[d]["close"] for d in ds]
        for i in range(60,len(ds)-21):
            d=ds[i]
            ma20=statistics.mean(closes[i-19:i+1]);ma60=statistics.mean(closes[i-59:i+1])
            px=closes[i]
            if px>100:continue
            rows.append({"symbol":sym,"date":d,
                         "trend_ma20":(px/ma20-1)*100 if ma20 else None,
                         "trend_ma60":(px/ma60-1)*100 if ma60 else None})
    bydate=defaultdict(list)
    for r in rows:bydate[r["date"]].append(r)
    out=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if r["trend_ma20"] is not None and r["trend_ma60"] is not None]
        if len(valid)<20:continue
        breadth=sum(r["trend_ma20"]>0 for r in valid)/len(valid)
        med60=statistics.median(r["trend_ma60"] for r in valid)
        regime="bull" if breadth>=0.55 and med60>0 else "bear" if breadth<=0.45 and med60<0 else "neutral"
        for r in valid:
            r["market_breadth20"]=breadth;r["regime"]=regime;out.append(r)
    return out

def zfit(rows):
    st={}
    for f in FEATURES:
        xs=[r[f] for r in rows]
        st[f]=(statistics.mean(xs),statistics.pstdev(xs) or 1)
    return st

def score(r,st):
    return sum(WEIGHTS[f]*((r[f]-st[f][0])/st[f][1]) for f in FEATURES)

def basket_return(names,start_idx,end_idx,dates,bysym,cost):
    vals=[]
    for sym in names:
        ds=dates
        if start_idx+1>=len(ds) or end_idx>=len(ds):continue
        ed=ds[start_idx+1]; xd=ds[end_idx]
        if ed not in bysym[sym] or xd not in bysym[sym]:continue
        entry=bysym[sym][ed]["open"];exitp=bysym[sym][xd]["close"]
        if entry and exitp:
            vals.append((exitp/entry-1)*100-cost)
    return statistics.mean(vals) if vals else None

def simulate(rows,bysym,dates,st,q90,rebalance,holdings,cost):
    rbd=defaultdict(list)
    for r in rows:
        if r["regime"] not in {"bear","neutral"}:continue
        sc=score(r,st)
        if sc>=q90:
            x=dict(r);x["score"]=sc;rbd[r["date"]].append(x)
    date_index={d:i for i,d in enumerate(dates)}
    equity=1.0;peak=1.0;maxdd=0.0;period_returns=[];n_reb=0
    eligible_dates=sorted(rbd)
    if not eligible_dates:return {"n":0}
    first_idx=date_index[eligible_dates[0]]
    last_idx=date_index[eligible_dates[-1]]
    i=first_idx
    while i+rebalance<len(dates) and i<=last_idx:
        d=dates[i]
        cands=rbd.get(d,[])
        if cands:
            # Broad basket: take holdings closest to center of eligible score distribution,
            # avoiding extreme-rank dependence.
            s=sorted(cands,key=lambda x:x["score"])
            if len(s)>holdings:
                mid=len(s)//2;lo=max(0,mid-holdings//2); picks=s[lo:lo+holdings]
            else:picks=s
            end_idx=min(i+rebalance,len(dates)-1)
            pr=basket_return([x["symbol"] for x in picks],i,end_idx,dates,bysym,cost)
            if pr is not None:
                equity*=1+pr/100
                peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
                period_returns.append(pr);n_reb+=1
        i+=rebalance
    m=metrics(period_returns)
    return {**m,"total_return_pct":(equity-1)*100,"max_drawdown_pct":maxdd*100,"rebalances":n_reb}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_calendar_basket")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    bysym,dates=load_daily(args.history_dir)
    rows=build_features(bysym,dates)
    train=[r for r in rows if int(r["date"][:4])<=2024]
    valid=[r for r in rows if int(r["date"][:4])==2025]
    test=[r for r in rows if int(r["date"][:4])==2026]
    st=zfit(train);scores=sorted(score(r,st) for r in train);q90=scores[int(.90*(len(scores)-1))]
    report={"method":"Calendar-rebalanced broad basket","rebalance_days":REBALANCE_DAYS,"holdings":HOLDINGS,"costs":COSTS,
            "q90":q90,"results":{},"production_eligible":False,
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","2026 is not fresh untouched OOS."]}
    cands=[]
    for rb in REBALANCE_DAYS:
      for h in HOLDINGS:
       for c in COSTS:
        key=f"R{rb}_H{h}_C{c:.2f}"
        report["results"][key]={}
        for sp,arr in (("train",train),("valid",valid),("test",test)):
            report["results"][key][sp]=simulate(arr,bysym,dates,st,q90,rb,h,c)
        r=report["results"][key]
        if all(r[s].get("n",0)>=10 for s in ("train","valid","test")):
            worst_exp=min(r[s].get("expectancy_pct",-999) for s in ("train","valid","test"))
            worst_pf=min(r[s].get("pf") or 0 for s in ("train","valid","test"))
            cands.append((worst_exp,worst_pf,key))
    cands.sort(reverse=True)
    report["best_worst_case"]=cands[0][2] if cands else None
    if cands:report["best_metrics"]=report["results"][cands[0][2]]
    (out/"calendar_basket_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Calendar-Rebalanced Broad Basket",f"- Best worst-case: {report['best_worst_case']}"]
    if report["best_worst_case"]:
        for sp in ("train","valid","test"):lines.append(f"- {sp}: {report['best_metrics'][sp]}")
    (out/"calendar_basket_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
