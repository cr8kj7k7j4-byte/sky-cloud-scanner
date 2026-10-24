from __future__ import annotations
import argparse,json,statistics,math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HORIZONS=[10,15]
TOP_NS=[3,5,10]
MAX_POSITIONS=[3,5,10]
COSTS=[0.45,0.65]
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
    eq=[]; x=0.0; peak=0.0; maxdd=0.0
    for v in vals:
        x+=v; peak=max(peak,x); maxdd=min(maxdd,x-peak); eq.append(x)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "sum_return_pct":sum(vals),"max_drawdown_pct":maxdd}

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
    raw=[]; nextmap={}
    for sym,days in bysym.items():
        closes=[x["close"] for x in days]
        for i in range(60,len(days)-16):
            ma20=statistics.mean(closes[i-19:i+1]); ma60=statistics.mean(closes[i-59:i+1])
            entry=days[i+1]["open"]
            if entry is None or entry>100:continue
            rec={"symbol":sym,"signal_date":days[i]["date"],"entry_date":days[i+1]["date"],
                 "entry":entry,
                 "trend_ma20":(closes[i]/ma20-1)*100 if ma20 else None,
                 "trend_ma60":(closes[i]/ma60-1)*100 if ma60 else None}
            for h in HORIZONS:
                rec[f"exit_date_{h}"]=days[i+h]["date"]
                rec[f"ret_{h}d"]=(days[i+h]["close"]/entry-1)*100
            raw.append(rec)
    bydate=defaultdict(list)
    for r in raw:bydate[r["signal_date"]].append(r)
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

def portfolio_sim(rows,h,topn,maxpos,cost,threshold,st,w,regime_filter):
    by_signal=defaultdict(list)
    for r in rows:
        if regime_filter and r["regime"] not in regime_filter: continue
        s=score(r,st,w)
        if s<threshold:continue
        by_signal[r["signal_date"]].append((s,r))
    open_positions=[]
    trades=[]
    for d in sorted(by_signal):
        # release positions whose exit date is before/equal new signal date
        open_positions=[p for p in open_positions if p["exit_date"]>d]
        slots=maxpos-len(open_positions)
        if slots<=0:continue
        cand=sorted(by_signal[d],key=lambda x:x[0],reverse=True)[:topn]
        for s,r in cand[:slots]:
            ret=r[f"ret_{h}d"]-cost
            tr={"symbol":r["symbol"],"signal_date":d,"entry_date":r["entry_date"],
                "exit_date":r[f"exit_date_{h}"],"net_return_pct":ret,"score":s,"regime":r["regime"]}
            open_positions.append(tr);trades.append(tr)
    vals=[t["net_return_pct"] for t in trades]
    return metrics(vals),trades

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--history-dir",required=True);ap.add_argument("--out",default="research_output_swing_portfolio")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    rows=build_rows(load_daily(args.history_dir))
    train=[r for r in rows if int(r["signal_date"][:4])<=2024]
    valid=[r for r in rows if int(r["signal_date"][:4])==2025]
    test=[r for r in rows if int(r["signal_date"][:4])==2026]

    # Freeze 5D-derived weights from prior robustness design using train only.
    audits={}
    for f in FEATURES:
        ti=spearman([r[f] for r in train],[r["ret_5d"] if "ret_5d" in r else 0 for r in train]) if False else None
    # hard-freeze previously validated weights
    w={"trend_ma20":-0.40057899619646997,"trend_ma60":-0.2106838328193073,"market_breadth20":-0.3887371709842227}
    st=zfit(train)
    train_scores=sorted(score(r,st,w) for r in train)
    q90=train_scores[int(0.90*(len(train_scores)-1))]

    regimes={"ALL":None,"WEAK_ONLY":{"bear"},"NON_BULL":{"bear","neutral"}}
    report={"method":"P0-LAB Weak-Regime Mean-Reversion Portfolio Backtest",
            "features":FEATURES,"weights":w,"train_q90":q90,
            "horizons":HORIZONS,"top_ns":TOP_NS,"max_positions":MAX_POSITIONS,"costs":COSTS,
            "split_counts":{"train":len(train),"valid":len(valid),"test":len(test)},
            "results":{},"best_validation":None,"production_eligible":False,
            "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample.","No fresh untouched OOS; 2026 previously observed.","Correlation modeled only indirectly via max positions, not sector covariance matrix."]}

    candidates=[]
    for h in HORIZONS:
      for topn in TOP_NS:
       for maxp in MAX_POSITIONS:
        if topn>maxp*2: continue
        for c in COSTS:
         for rgname,rgset in regimes.items():
          key=f"{h}D_T{topn}_M{maxp}_C{c:.2f}_{rgname}"
          report["results"][key]={}
          for sp,arr in (("train",train),("valid",valid),("test",test)):
              m,_=portfolio_sim(arr,h,topn,maxp,c,q90,st,w,rgset)
              report["results"][key][sp]=m
          v=report["results"][key]["valid"];t=report["results"][key]["test"];tr=report["results"][key]["train"]
          if v.get("n",0)>=50 and t.get("n",0)>=50:
              candidates.append((v.get("expectancy_pct",-999),v.get("pf") or 0,key))
    candidates.sort(reverse=True)
    best=candidates[0][2] if candidates else None
    report["best_validation"]=best
    if best:
        report["best_result"]=report["results"][best]
        br=report["results"][best]
        report["research_gate_pass"]=bool(
            all((br[s].get("expectancy_pct") or -999)>0 and (br[s].get("pf") or 0)>1.05 for s in ("train","valid","test"))
        )
    else:report["research_gate_pass"]=False

    (out/"portfolio_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Weak-Regime Mean-Reversion Portfolio Backtest",f"- Split counts: {report['split_counts']}",f"- Best validation config: {best}",f"- Research gate pass: **{report['research_gate_pass']}**"]
    if best:
        for sp in ("train","valid","test"):
            m=report["results"][best][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')} maxDD={m.get('max_drawdown_pct')}")
    (out/"portfolio_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
