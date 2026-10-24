from __future__ import annotations
import argparse,json,statistics
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
            if entry is None or entry>100: continue
            raw.append({
                "symbol":sym,"signal_date":days[i]["date"],"entry_date":days[i+1]["date"],
                "exit_date":days[i+H]["date"],
                "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None,
                "ret":(days[i+H]["close"]/entry-1)*100-COST
            })
    bydate=defaultdict(list)
    for r in raw: bydate[r["signal_date"]].append(r)
    out=[]
    for d,arr in bydate.items():
        valid=[r for r in arr if r["trend_ma20"] is not None and r["trend_ma60"] is not None]
        if len(valid)<20: continue
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
        st[f]=(statistics.mean(xs),statistics.pstdev(xs) or 1.0)
    return st

def score(r,st):
    return sum(WEIGHTS[f]*((r[f]-st[f][0])/st[f][1]) for f in FEATURES)

def capital_weighted_portfolio(rows,q90,st,topn=3,maxpos=5,regimes={"bear","neutral"}):
    bysig=defaultdict(list)
    for r in rows:
        s=score(r,st)
        if s>=q90 and r["regime"] in regimes:
            bysig[r["signal_date"]].append((s,r))
    active=[]
    trades=[]
    equity=1.0
    peak=1.0
    maxdd=0.0
    equity_points=[]
    for d in sorted(bysig):
        # settle exits up to current signal date
        remain=[]
        exits=[]
        for p in active:
            if p["exit_date"]<=d: exits.append(p)
            else: remain.append(p)
        if exits:
            # equal capital allocation at entry, realized independently
            for p in exits:
                equity *= (1 + p["weight"] * p["ret"]/100.0)
            peak=max(peak,equity); maxdd=min(maxdd,equity/peak-1.0)
            equity_points.append({"date":d,"equity":equity})
        active=remain
        slots=maxpos-len(active)
        if slots<=0: continue
        cand=sorted(bysig[d],key=lambda x:x[0],reverse=True)[:topn]
        alloc=min(slots,len(cand))
        if alloc<=0: continue
        # fixed fraction of total capital per slot
        w=1.0/maxpos
        for s,r in cand[:alloc]:
            tr={**r,"score":s,"weight":w}
            active.append(tr);trades.append(tr)
    # settle rest
    for p in sorted(active,key=lambda x:x["exit_date"]):
        equity *= (1 + p["weight"] * p["ret"]/100.0)
        peak=max(peak,equity); maxdd=min(maxdd,equity/peak-1.0)
    return {
        "trades":trades,
        "trade_metrics":metrics([t["ret"] for t in trades]),
        "final_equity":equity,
        "total_return_pct":(equity-1)*100,
        "max_drawdown_pct":maxdd*100
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_portfolio_audit")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["signal_date"][:4])<=2024]
    valid=[r for r in rows if int(r["signal_date"][:4])==2025]
    test=[r for r in rows if int(r["signal_date"][:4])==2026]
    st=zfit(train)
    scores=sorted(score(r,st) for r in train);q90=scores[int(.90*(len(scores)-1))]

    report={"method":"Portfolio decomposition audit","horizon_days":H,"cost_pct":COST,"q90":q90,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},"splits":{}}
    for name,arr in (("train",train),("valid",valid),("test",test)):
        elig=[r for r in arr if score(r,st)>=q90 and r["regime"] in {"bear","neutral"}]
        bydate=defaultdict(list)
        for r in elig:bydate[r["signal_date"]].append(r)
        top3=[]
        for d,a in bydate.items():
            top3.extend([r for _,r in sorted([(score(r,st),r) for r in a],reverse=True,key=lambda x:x[0])[:3]])
        port=capital_weighted_portfolio(arr,q90,st,3,5,{"bear","neutral"})
        report["splits"][name]={
            "all_eligible":metrics([r["ret"] for r in elig]),
            "top3_without_capacity":metrics([r["ret"] for r in top3]),
            "portfolio_trade_metrics":port["trade_metrics"],
            "final_equity":port["final_equity"],
            "total_return_pct":port["total_return_pct"],
            "max_drawdown_pct":port["max_drawdown_pct"],
            "signal_days":len(bydate),
            "avg_candidates_per_signal_day":statistics.mean([len(v) for v in bydate.values()]) if bydate else 0,
            "median_candidates_per_signal_day":statistics.median([len(v) for v in bydate.values()]) if bydate else 0
        }
    (out/"portfolio_decomposition_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Portfolio Decomposition Audit"]
    for sp in ("train","valid","test"):
        x=report["splits"][sp]
        lines.append(f"\n## {sp}")
        lines.append(f"- all eligible: {x['all_eligible']}")
        lines.append(f"- top3 no capacity: {x['top3_without_capacity']}")
        lines.append(f"- portfolio trades: {x['portfolio_trade_metrics']}")
        lines.append(f"- total return={x['total_return_pct']:.3f}% maxDD={x['max_drawdown_pct']:.3f}%")
        lines.append(f"- signal days={x['signal_days']} avg candidates/day={x['avg_candidates_per_signal_day']:.2f}")
    (out/"portfolio_decomposition_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))
if __name__=="__main__":main()
