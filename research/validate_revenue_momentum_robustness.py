from __future__ import annotations
import argparse,json,statistics,math
from collections import defaultdict
from datetime import datetime,date
from pathlib import Path
import pandas as pd

CANDIDATES=[
    ("mom",5,1),
    ("yoy",5,1),
    ("yoy_accel",5,1),
    ("yoy",20,1),
]
COSTS=[0.20,0.45,0.65]
QUANTILES=[0.05,0.10,0.20]

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
    eq=1.0;peak=1.0;maxdd=0.0
    for v in vals:
        eq*=1+v/100
        peak=max(peak,eq)
        maxdd=min(maxdd,eq/peak-1)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals),
            "total_return_pct":(eq-1)*100,
            "max_drawdown_pct":maxdd*100}

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
    rows=df.to_dict("records");by=defaultdict(list);out=[]
    for r in rows:
        r["symbol"]=str(r["symbol"]).replace(".0","")
        r["year"]=int(r["year"]);r["month"]=int(r["month"])
        by[r["symbol"]].append(r)
    for sym,arr in by.items():
        arr.sort(key=lambda r:(r["year"],r["month"]))
        prev_yoy=None;hist=[]
        for r in arr:
            rev=fnum(r.get("revenue"));yoy=fnum(r.get("yoy"));mom=fnum(r.get("mom"));cum=fnum(r.get("cum_yoy"))
            lyr=fnum(r.get("last_year_revenue"));prev=fnum(r.get("prev_revenue"))
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
        i=lookup[sym][kd];days=bysym[sym];entry=days[i]["open"]
        if entry is None or entry>100:continue
        e={**r,"knowledge_date":kd,"entry":entry}
        for h in {5,20}:
            j=i+h
            if j<len(days):e[f"ret_{h}d"]=(days[j]["close"]/entry-1)*100
        ev.append(e)
    return ev

def pick_quantile(arr,feature,horizon,sign,q):
    target=f"ret_{horizon}d"
    a=[x for x in arr if x.get(feature) is not None and x.get(target) is not None]
    if not a:return []
    a=sorted(a,key=lambda x:x[feature]);k=max(1,int(len(a)*q))
    return a[-k:] if sign>0 else a[:k]

def group_metrics(rows,target,cost,keyfunc):
    groups=defaultdict(list)
    for x in rows:groups[str(keyfunc(x))].append(x[target]-cost)
    return {k:metrics(v) for k,v in sorted(groups.items())}

def concentration(rows):
    if not rows:return {}
    n=len(rows)
    bysym=defaultdict(int);bymkt=defaultdict(int)
    for r in rows:
        bysym[r["symbol"]]+=1
        bymkt[str(r.get("market","UNKNOWN"))]+=1
    top_symbols=sorted(bysym.items(),key=lambda kv:kv[1],reverse=True)[:10]
    return {
        "top_symbol_share":top_symbols[0][1]/n if top_symbols else 0,
        "top5_symbol_share":sum(v for _,v in top_symbols[:5])/n if top_symbols else 0,
        "top10_symbols":top_symbols,
        "market_shares":{k:v/n for k,v in bymkt.items()}
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--revenue-csv",required=True)
    ap.add_argument("--out",default="research_output_revenue_robust")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    bysym,trading=load_prices(args.history_dir)
    events=build_events(prepare_revenue(args.revenue_csv),bysym,trading)

    splits={
        "train":[e for e in events if int(e["knowledge_date"][:4])<=2024],
        "valid":[e for e in events if int(e["knowledge_date"][:4])==2025],
        "test":[e for e in events if int(e["knowledge_date"][:4])==2026],
    }
    report={"method":"Frozen Revenue Momentum Candidate Robustness",
            "candidates":[],"split_counts":{k:len(v) for k,v in splits.items()},
            "costs":COSTS,"quantiles":QUANTILES,"point_in_time_verified":False,
            "promotion_blocked_reason":"Actual company filing timestamp not yet aligned.",
            "production_eligible":False,
            "limitations":["Current-universe survivorship bias from price sample.","Knowledge-date uses conservative statutory deadline proxy.","No company-level filing timestamp yet.","2026 is not globally untouched OOS."]}

    for feature,h,sign in CANDIDATES:
        target=f"ret_{h}d"
        c={"name":f"{feature}_{h}d","feature":feature,"horizon":h,"sign":sign,"results":{}}
        for q in QUANTILES:
            qk=f"q{int(q*100)}"
            c["results"][qk]={}
            for cost in COSTS:
                ck=f"{cost:.2f}"
                c["results"][qk][ck]={}
                for sp,arr in splits.items():
                    chosen=pick_quantile(arr,feature,h,sign,q)
                    vals=[x[target]-cost for x in chosen]
                    base=metrics(vals)
                    base["concentration"]=concentration(chosen)
                    base["yearly"]=group_metrics(chosen,target,cost,lambda x:x["knowledge_date"][:4])
                    base["market"]=group_metrics(chosen,target,cost,lambda x:x.get("market","UNKNOWN"))
                    c["results"][qk][ck][sp]=base
        # formal robustness gate frozen at top decile and 0.45 primary, 0.65 stress
        primary=c["results"]["q10"]["0.45"]
        stress=c["results"]["q10"]["0.65"]
        primary_pass=all(primary[s].get("n",0)>=50 and (primary[s].get("expectancy_pct") or -999)>0 and (primary[s].get("pf") or 0)>1.05 for s in ("train","valid","test"))
        stress_pass=all(stress[s].get("n",0)>=50 and (stress[s].get("expectancy_pct") or -999)>0 and (stress[s].get("pf") or 0)>1.0 for s in ("train","valid","test"))
        concentration_pass=all(primary[s]["concentration"].get("top5_symbol_share",1)<=0.35 for s in ("train","valid","test"))
        c["robustness_gate"]={"primary_045":primary_pass,"stress_065":stress_pass,"concentration":concentration_pass,
                              "pass":bool(primary_pass and stress_pass and concentration_pass)}
        report["candidates"].append(c)

    report["pre_pit_candidates"]=[c["name"] for c in report["candidates"] if c["robustness_gate"]["pass"]]
    report["passing_candidates"]=[]
    (out/"revenue_robustness_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Revenue Momentum Candidate Robustness",
           f"- Split counts: {report['split_counts']}",
           f"- Pre-PIT candidates: {report['pre_pit_candidates']}",
           f"- Point-in-time verified: {report['point_in_time_verified']}",
           f"- Promotion candidates: {report['passing_candidates']}"]
    for c in report["candidates"]:
        lines.append(f"\n## {c['name']}")
        lines.append(f"- Gate: {c['robustness_gate']}")
        for sp in ("train","valid","test"):
            p=c["results"]["q10"]["0.45"][sp]
            s=c["results"]["q10"]["0.65"][sp]
            lines.append(f"- {sp} @0.45: n={p['n']} exp={p.get('expectancy_pct')} PF={p.get('pf')} MDD={p.get('max_drawdown_pct')} top5share={p['concentration'].get('top5_symbol_share')}")
            lines.append(f"- {sp} @0.65: n={s['n']} exp={s.get('expectancy_pct')} PF={s.get('pf')}")
    (out/"revenue_robustness_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
