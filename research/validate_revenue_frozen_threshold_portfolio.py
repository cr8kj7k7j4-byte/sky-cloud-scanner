from __future__ import annotations
import argparse,json,statistics,math
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
import pandas as pd

CANDIDATES=[("mom",5),("yoy_accel",5)]
COSTS=[0.45,0.65]
MAX_POSITIONS=[5,10,15]
TOP_NS=[3,5,10]

def fnum(x):
    try:
        if x is None:return None
        s=str(x).strip().replace(",","").replace("%","")
        if s in ("","nan","NaN","None","--","-"):return None
        return float(s)
    except Exception:return None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals)}

def load_prices(history_dir):
    bysym={};trading=set()
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
    ny,nm=next_month(y,m);cutoff=date(ny,nm,10).isoformat()
    for d in trading:
        if d>cutoff:return d
    return None

def prepare_revenue(csv_path):
    df=pd.read_csv(csv_path,dtype={"symbol":str})
    by=defaultdict(list);out=[]
    for r in df.to_dict("records"):
        r["symbol"]=str(r["symbol"]).replace(".0","")
        r["year"]=int(r["year"]);r["month"]=int(r["month"])
        by[r["symbol"]].append(r)
    for sym,arr in by.items():
        arr.sort(key=lambda r:(r["year"],r["month"]))
        prev_yoy=None
        for r in arr:
            rev=fnum(r.get("revenue"));yoy=fnum(r.get("yoy"));mom=fnum(r.get("mom"))
            lyr=fnum(r.get("last_year_revenue"));prev=fnum(r.get("prev_revenue"))
            if yoy is None and rev is not None and lyr not in (None,0):yoy=(rev/lyr-1)*100
            if mom is None and rev is not None and prev not in (None,0):mom=(rev/prev-1)*100
            accel=yoy-prev_yoy if yoy is not None and prev_yoy is not None else None
            out.append({**r,"yoy":yoy,"mom":mom,"yoy_accel":accel})
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
        i=lookup[sym][kd];days=bysym[sym];entry=days[i]["open"]
        if entry is None or entry>100:continue
        j=i+5
        if j>=len(days):continue
        ev.append({**r,"knowledge_date":kd,"entry_date":days[i]["date"],
                   "exit_date":days[j]["date"],"ret_5d":(days[j]["close"]/entry-1)*100})
    return ev

def quantile_threshold(vals,q=.90):
    xs=sorted(vals)
    if not xs:return None
    return xs[int(q*(len(xs)-1))]

def selected(arr,feature,thr):
    return [x for x in arr if x.get(feature) is not None and x[feature]>=thr]

def concentration(rows):
    if not rows:return {"top5_symbol_share":None,"market_shares":{}}
    n=len(rows);sym=defaultdict(int);mkt=defaultdict(int)
    for r in rows:
        sym[r["symbol"]]+=1;mkt[str(r.get("market","UNKNOWN"))]+=1
    ss=sorted(sym.values(),reverse=True)
    return {"top5_symbol_share":sum(ss[:5])/n,
            "market_shares":{k:v/n for k,v in mkt.items()}}

def portfolio(arr,feature,thr,cost,topn,maxpos):
    # All events on the same knowledge_date are ranked by the frozen feature;
    # entry/exit dates come from the conservative PIT proxy.
    bydate=defaultdict(list)
    for r in selected(arr,feature,thr):
        bydate[r["knowledge_date"]].append(r)
    active=[];trades=[];equity=1.0;peak=1.0;maxdd=0.0
    for d in sorted(bydate):
        # settle exits before/equal this signal date
        active=[p for p in active if p["exit_date"]>d]
        slots=maxpos-len(active)
        if slots<=0:continue
        cand=sorted(bydate[d],key=lambda x:x[feature],reverse=True)[:topn]
        for r in cand[:slots]:
            tr={**r,"net_return_pct":r["ret_5d"]-cost}
            trades.append(tr);active.append(tr)
            # equal-weight at max-position capacity; this is a research approximation
            step=tr["net_return_pct"]/100/maxpos
            equity*=1+step
            peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
    vals=[t["net_return_pct"] for t in trades]
    return {**metrics(vals),"total_return_pct":(equity-1)*100,
            "max_drawdown_pct":maxdd*100,"concentration":concentration(trades)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--revenue-csv",required=True)
    ap.add_argument("--out",default="research_output_revenue_frozen")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    bysym,trading=load_prices(args.history_dir)
    events=build_events(prepare_revenue(args.revenue_csv),bysym,trading)
    splits={"train":[e for e in events if int(e["knowledge_date"][:4])<=2024],
            "valid":[e for e in events if int(e["knowledge_date"][:4])==2025],
            "test":[e for e in events if int(e["knowledge_date"][:4])==2026]}

    report={"method":"Revenue frozen-threshold + portfolio validation",
            "split_counts":{k:len(v) for k,v in splits.items()},
            "candidates":{},"production_eligible":False,
            "limitations":["Conservative statutory-deadline PIT proxy, not company filing timestamp.",
                           "Current-universe survivorship bias from 100-stock price sample.",
                           "2026 is not globally untouched OOS.",
                           "Portfolio equity uses equal slot-weight research approximation."]}

    for feature,h in CANDIDATES:
        train_vals=[e[feature] for e in splits["train"] if e.get(feature) is not None]
        thr=quantile_threshold(train_vals,.90)
        info={"train_q90_threshold":thr,"selection":{},"portfolio":{}}
        for cost in COSTS:
            ck=f"{cost:.2f}";info["selection"][ck]={}
            for sp,arr in splits.items():
                ch=selected(arr,feature,thr)
                info["selection"][ck][sp]={**metrics([x["ret_5d"]-cost for x in ch]),
                                           "concentration":concentration(ch)}
        for topn in TOP_NS:
            for mp in MAX_POSITIONS:
                key=f"T{topn}_M{mp}"
                info["portfolio"][key]={}
                for cost in COSTS:
                    ck=f"{cost:.2f}"
                    info["portfolio"][key][ck]={sp:portfolio(arr,feature,thr,cost,topn,mp)
                                               for sp,arr in splits.items()}
        # choose best worst-case portfolio based only on validation, then report test honestly
        configs=[]
        for key,x in info["portfolio"].items():
            v=x["0.45"]["valid"]
            if v.get("n",0)>=20:
                configs.append((v.get("expectancy_pct",-999),v.get("pf") or 0,key))
        configs.sort(reverse=True)
        best=configs[0][2] if configs else None
        info["best_validation_config"]=best
        if best:
            p=info["portfolio"][best]
            info["gate"]={
                "frozen_threshold_045":all(p["0.45"][s].get("n",0)>=20 and (p["0.45"][s].get("expectancy_pct") or -999)>0 and (p["0.45"][s].get("pf") or 0)>1.05 for s in ("train","valid","test")),
                "stress_065":all(p["0.65"][s].get("n",0)>=20 and (p["0.65"][s].get("expectancy_pct") or -999)>0 and (p["0.65"][s].get("pf") or 0)>1.0 for s in ("train","valid","test")),
                "concentration":all((p["0.45"][s]["concentration"].get("top5_symbol_share") or 1)<=0.35 for s in ("train","valid","test")),
            }
            info["gate"]["pass"]=all(info["gate"].values())
        else:
            info["gate"]={"pass":False}
        report["candidates"][f"{feature}_{h}d"]=info

    report["passing_candidates"]=[k for k,v in report["candidates"].items() if v["gate"].get("pass")]
    (out/"revenue_frozen_portfolio_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Revenue Frozen Threshold + Portfolio Validation",
           f"- Split counts: {report['split_counts']}",
           f"- Passing candidates: {report['passing_candidates']}"]
    for name,info in report["candidates"].items():
        lines.append(f"\n## {name}")
        lines.append(f"- Train q90 threshold: {info['train_q90_threshold']}")
        lines.append(f"- Best validation config: {info['best_validation_config']}")
        lines.append(f"- Gate: {info['gate']}")
        if info["best_validation_config"]:
            best=info["portfolio"][info["best_validation_config"]]
            for sp in ("train","valid","test"):
                a=best["0.45"][sp];b=best["0.65"][sp]
                lines.append(f"- {sp} @0.45: n={a['n']} exp={a.get('expectancy_pct')} PF={a.get('pf')} MDD={a.get('max_drawdown_pct')} top5={a['concentration'].get('top5_symbol_share')}")
                lines.append(f"- {sp} @0.65: n={b['n']} exp={b.get('expectancy_pct')} PF={b.get('pf')}")
    (out/"revenue_frozen_portfolio_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
