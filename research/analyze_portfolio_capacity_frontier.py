from __future__ import annotations
import argparse,json,statistics,hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path

H=15
COST=0.45
FEATURES=["trend_ma20","trend_ma60","market_breadth20"]
WEIGHTS={"trend_ma20":-0.40057899619646997,"trend_ma60":-0.2106838328193073,"market_breadth20":-0.3887371709842227}
MAX_POSITIONS=[5,10,15,20,30]
DAILY_NEW=[1,2,3,5,10]

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
        closes=[x["close"] for x in days]
        for i in range(60,len(days)-H-1):
            ma20=statistics.mean(closes[i-19:i+1]); ma60=statistics.mean(closes[i-59:i+1])
            entry=days[i+1]["open"]
            if entry is None or entry>100:continue
            raw.append({"symbol":sym,"signal_date":days[i]["date"],"entry_date":days[i+1]["date"],
                        "exit_date":days[i+H]["date"],
                        "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                        "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None,
                        "ret":(days[i+H]["close"]/entry-1)*100-COST})
    bydate=defaultdict(list)
    for r in raw:bydate[r["signal_date"]].append(r)
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

def pick(cands,n,mode):
    if mode=="HASH":
        return sorted(cands,key=lambda r:hashlib.sha256((r["signal_date"]+"|"+r["symbol"]).encode()).hexdigest())[:n]
    if mode=="MIDDLE":
        s=sorted(cands,key=lambda r:r["score"]); mid=len(s)//2; lo=max(0,mid-n//2); return s[lo:lo+n]
    if mode=="SPREAD":
        s=sorted(cands,key=lambda r:r["score"])
        if len(s)<=n:return s
        idx=[round(i*(len(s)-1)/(n-1)) for i in range(n)] if n>1 else [len(s)//2]
        return [s[i] for i in idx]
    return sorted(cands,key=lambda r:r["score"],reverse=True)[:n]

def sim(rows,q90,st,maxpos,daily_new,mode):
    bydate=defaultdict(list)
    for r in rows:
        if r["regime"] not in {"bear","neutral"}:continue
        sc=score(r,st)
        if sc>=q90:
            x=dict(r);x["score"]=sc;bydate[r["signal_date"]].append(x)
    active=[];trades=[];equity=1.0;peak=1.0;maxdd=0.0
    daily_util=[]
    for d in sorted(bydate):
        exits=[p for p in active if p["exit_date"]<=d]
        active=[p for p in active if p["exit_date"]>d]
        for p in exits:
            equity*=1+(1/maxpos)*p["ret"]/100
            peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
        slots=maxpos-len(active)
        daily_util.append(len(active)/maxpos)
        if slots<=0:continue
        n=min(slots,daily_new)
        for r in pick(bydate[d],n,mode):
            active.append(r);trades.append(r)
    for p in sorted(active,key=lambda x:x["exit_date"]):
        equity*=1+(1/maxpos)*p["ret"]/100
        peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
    return {"trade_metrics":metrics([t["ret"] for t in trades]),
            "total_return_pct":(equity-1)*100,
            "max_drawdown_pct":maxdd*100,
            "avg_utilization":statistics.mean(daily_util) if daily_util else 0,
            "n_trades":len(trades)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_capacity")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["signal_date"][:4])<=2024]
    valid=[r for r in rows if int(r["signal_date"][:4])==2025]
    test=[r for r in rows if int(r["signal_date"][:4])==2026]
    st=zfit(train);scores=sorted(score(r,st) for r in train);q90=scores[int(.90*(len(scores)-1))]
    modes=["TOP","MIDDLE","HASH","SPREAD"]
    report={"method":"Portfolio breadth/capacity frontier","horizon_days":H,"cost_pct":COST,
            "max_positions":MAX_POSITIONS,"daily_new_limits":DAILY_NEW,"modes":modes,
            "q90":q90,"results":{},"production_eligible":False}
    cands=[]
    for mp in MAX_POSITIONS:
      for dn in DAILY_NEW:
       if dn>mp:continue
       for mode in modes:
        key=f"M{mp}_D{dn}_{mode}"
        report["results"][key]={}
        for sp,arr in (("train",train),("valid",valid),("test",test)):
            report["results"][key][sp]=sim(arr,q90,st,mp,dn,mode)
        r=report["results"][key]
        if all(r[s]["trade_metrics"].get("n",0)>=50 for s in ("train","valid","test")):
            worst_exp=min(r[s]["trade_metrics"].get("expectancy_pct",-999) for s in ("train","valid","test"))
            worst_pf=min(r[s]["trade_metrics"].get("pf") or 0 for s in ("train","valid","test"))
            cands.append((worst_exp,worst_pf,key))
    cands.sort(reverse=True)
    report["best_worst_case"]=cands[0][2] if cands else None
    if cands:
        report["best_worst_case_metrics"]=report["results"][cands[0][2]]
    (out/"capacity_frontier_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Portfolio Breadth / Capacity Frontier",f"- Best worst-case config: {report['best_worst_case']}"]
    if report["best_worst_case"]:
        for sp in ("train","valid","test"):
            x=report["best_worst_case_metrics"][sp]
            lines.append(f"- {sp}: {x}")
    (out/"capacity_frontier_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":main()
