from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
import pandas as pd

CANDIDATES=[("mom",5,1),("yoy_accel",5,1)]
MAX_POSITIONS=[5,10,15]
DAILY_NEW=[3,5,10]
COSTS=[0.45,0.65]

def fnum(x):
    try:
        if x is None:return None
        s=str(x).strip().replace(",","").replace("%","")
        if s in ("","nan","NaN","None","--","-"):return None
        return float(s)
    except Exception:return None

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

def next_month(y,m): return (y+1,1) if m==12 else (y,m+1)

def knowledge_date(y,m,trading):
    ny,nm=next_month(y,m); cutoff=date(ny,nm,10).isoformat()
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
        if entry is None or entry>100 or i+5>=len(days):continue
        ev.append({**r,"knowledge_date":kd,"entry_date":kd,"exit_date":days[i+5]["date"],
                   "ret_5d":(days[i+5]["close"]/entry-1)*100})
    return ev

def train_threshold(events,feature):
    xs=sorted(e[feature] for e in events if e.get(feature) is not None)
    return xs[int(0.90*(len(xs)-1))]

def pf(vals):
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<0)
    return gp/gl if gl>0 else None

def simulate(events,feature,thr,maxpos,newcap,cost):
    bydate=defaultdict(list)
    for e in events:
        v=e.get(feature)
        if v is not None and v>=thr:bydate[e["knowledge_date"]].append(e)
    active=[];trades=[];equity=1.0;peak=1.0;maxdd=0.0
    # settle on signal dates and final dates; event cadence monthly so sufficient for implementation comparison
    for d in sorted(bydate):
        remain=[]
        for p in active:
            if p["exit_date"]<=d:
                equity*=1+(p["weight"]*p["net_ret"]/100)
                peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
            else:remain.append(p)
        active=remain
        held={p["symbol"] for p in active}
        slots=maxpos-len(active)
        if slots<=0:continue
        cand=[e for e in sorted(bydate[d],key=lambda x:x[feature],reverse=True) if e["symbol"] not in held]
        take=cand[:min(slots,newcap)]
        for e in take:
            tr={**e,"net_ret":e["ret_5d"]-cost,"weight":1.0/maxpos}
            active.append(tr);trades.append(tr)
    for p in sorted(active,key=lambda x:x["exit_date"]):
        equity*=1+(p["weight"]*p["net_ret"]/100)
        peak=max(peak,equity);maxdd=min(maxdd,equity/peak-1)
    vals=[t["net_ret"] for t in trades]
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals) if vals else None,
            "pf":pf(vals),"win_rate":sum(v>0 for v in vals)/len(vals) if vals else None,
            "total_return_pct":(equity-1)*100,"max_drawdown_pct":maxdd*100,
            "unique_symbols":len(set(t["symbol"] for t in trades)),
            "top5_symbol_share":(sum(v for _,v in sorted(
                ((s,sum(1 for t in trades if t["symbol"]==s)) for s in set(t["symbol"] for t in trades)),
                key=lambda x:x[1],reverse=True)[:5])/len(trades)) if trades else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--revenue-csv",required=True)
    ap.add_argument("--out",default="research_output_revenue_portfolio")
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    events=build_events(prepare_revenue(args.revenue_csv),*load_prices(args.history_dir))
    splits={"train":[e for e in events if int(e["knowledge_date"][:4])<=2024],
            "valid":[e for e in events if int(e["knowledge_date"][:4])==2025],
            "test":[e for e in events if int(e["knowledge_date"][:4])==2026]}
    report={"method":"Revenue Momentum Portfolio Validation","results":{},"production_eligible":False,
            "limitations":["Conservative statutory-deadline knowledge date, not actual filing timestamp.",
                           "Current-universe survivorship bias.","2026 not globally untouched OOS."]}
    for feature,h,sign in CANDIDATES:
        thr=train_threshold(splits["train"],feature)
        name=f"{feature}_{h}d";report["results"][name]={"threshold":thr,"configs":{}}
        candidates=[]
        for mp in MAX_POSITIONS:
          for nc in DAILY_NEW:
            if nc>mp:continue
            for cost in COSTS:
              key=f"M{mp}_N{nc}_C{cost:.2f}"
              rr={sp:simulate(arr,feature,thr,mp,nc,cost) for sp,arr in splits.items()}
              report["results"][name]["configs"][key]=rr
              if cost==0.45 and all(rr[s]["n"]>=20 for s in rr):
                  worst=min(rr[s]["expectancy_pct"] for s in rr if rr[s]["expectancy_pct"] is not None)
                  worstpf=min(rr[s]["pf"] or 0 for s in rr)
                  candidates.append((worst,worstpf,key))
        candidates.sort(reverse=True)
        best=candidates[0][2] if candidates else None
        report["results"][name]["best_worst_case_045"]=best
        if best:
            br=report["results"][name]["configs"][best]
            report["results"][name]["portfolio_gate_pass"]=bool(
                all((br[s]["expectancy_pct"] or -999)>0 and (br[s]["pf"] or 0)>1.05 and (br[s]["top5_symbol_share"] or 1)<=0.40 for s in ("train","valid","test"))
            )
        else:report["results"][name]["portfolio_gate_pass"]=False
    report["passing_candidates"]=[n for n,x in report["results"].items() if x.get("portfolio_gate_pass")]
    (out/"revenue_portfolio_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Revenue Momentum Portfolio Validation",f"- Passing candidates: {report['passing_candidates']}"]
    for n,x in report["results"].items():
        lines.append(f"\n## {n}")
        lines.append(f"- Threshold: {x['threshold']}")
        lines.append(f"- Best @0.45: {x['best_worst_case_045']}")
        lines.append(f"- Portfolio gate: {x['portfolio_gate_pass']}")
        if x["best_worst_case_045"]:
            for sp,m in x["configs"][x["best_worst_case_045"]].items():
                lines.append(f"- {sp}: {m}")
    (out/"revenue_portfolio_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
