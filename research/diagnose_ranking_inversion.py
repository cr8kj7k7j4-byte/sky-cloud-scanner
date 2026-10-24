from __future__ import annotations
import argparse,json,statistics,hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path

H=15
COST=0.45
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

def pick_day(cands,mode,k=3):
    if mode=="TOP": return sorted(cands,key=lambda x:x["score"],reverse=True)[:k]
    if mode=="BOTTOM": return sorted(cands,key=lambda x:x["score"])[:k]
    if mode=="MIDDLE":
        s=sorted(cands,key=lambda x:x["score"])
        mid=len(s)//2
        lo=max(0,mid-k//2)
        return s[lo:lo+k]
    if mode=="HASH":
        return sorted(cands,key=lambda x:hashlib.sha256((x["signal_date"]+"|"+x["symbol"]).encode()).hexdigest())[:k]
    if mode=="SPREAD":
        s=sorted(cands,key=lambda x:x["score"])
        if len(s)<=k:return s
        idx=[round(i*(len(s)-1)/(k-1)) for i in range(k)] if k>1 else [len(s)//2]
        return [s[i] for i in idx]
    return []

def capacity_sim(rows,q90,st,mode,k=3,maxpos=5):
    bydate=defaultdict(list)
    for r in rows:
        if r["regime"] not in {"bear","neutral"}:continue
        sc=score(r,st)
        if sc>=q90:
            x=dict(r);x["score"]=sc;bydate[r["signal_date"]].append(x)
    active=[];trades=[];equity=1.0;peak=1.0;maxdd=0.0
    for d in sorted(bydate):
        exits=[p for p in active if p["exit_date"]<=d]
        active=[p for p in active if p["exit_date"]>d]
        for p in exits:
            equity*=1+(1/maxpos)*p["ret"]/100
            peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
        slots=maxpos-len(active)
        if slots<=0:continue
        picks=pick_day(bydate[d],mode,k)[:slots]
        active.extend(picks);trades.extend(picks)
    for p in sorted(active,key=lambda x:x["exit_date"]):
        equity*=1+(1/maxpos)*p["ret"]/100
        peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
    return {"trade_metrics":metrics([t["ret"] for t in trades]),
            "total_return_pct":(equity-1)*100,"max_drawdown_pct":maxdd*100,
            "n_trades":len(trades)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_rank_diag")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["signal_date"][:4])<=2024]
    valid=[r for r in rows if int(r["signal_date"][:4])==2025]
    test=[r for r in rows if int(r["signal_date"][:4])==2026]
    st=zfit(train)
    scores=sorted(score(r,st) for r in train);q90=scores[int(.90*(len(scores)-1))]
    modes=["TOP","BOTTOM","MIDDLE","HASH","SPREAD"]
    report={"method":"P0-O ranking inversion diagnostic","q90":q90,"modes":modes,
            "splits":{},"production_eligible":False,
            "note":"Diagnostic only; HASH is deterministic pseudo-random control, not a strategy."}
    for sp,arr in (("train",train),("valid",valid),("test",test)):
        elig=[dict(r,score=score(r,st)) for r in arr if r["regime"] in {"bear","neutral"} and score(r,st)>=q90]
        bydate=defaultdict(list)
        for r in elig:bydate[r["signal_date"]].append(r)
        report["splits"][sp]={"all_eligible":metrics([r["ret"] for r in elig]),"selection":{}}
        for mode in modes:
            flat=[]
            for d,c in bydate.items():flat.extend(pick_day(c,mode,3))
            report["splits"][sp]["selection"][mode]={
                "no_capacity":metrics([r["ret"] for r in flat]),
                "capacity":capacity_sim(arr,q90,st,mode,3,5)
            }
    (out/"ranking_inversion_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky P0-O Ranking Inversion Diagnostic"]
    for sp in ("train","valid","test"):
        lines.append(f"\n## {sp}")
        lines.append(f"- all eligible: {report['splits'][sp]['all_eligible']}")
        for mode in modes:
            a=report["splits"][sp]["selection"][mode]
            lines.append(f"- {mode}: no_capacity={a['no_capacity']} capacity={a['capacity']}")
    (out/"ranking_inversion_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":main()
