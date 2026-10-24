from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def f(x,k):
    try:
        v=x.get(k); return None if v in (None,"") else float(v)
    except: return None

def dt(s): return datetime.fromisoformat(str(s))

def group_days(obj):
    by=defaultdict(list)
    for b in obj["data"]:
        x={**b,"_dt":dt(b["date"])}
        by[x["_dt"].date()].append(x)
    for d in by: by[d].sort(key=lambda z:z["_dt"])
    return by

def tick(px):
    return .01 if px<10 else .05 if px<50 else .1 if px<100 else .5 if px<500 else 1 if px<1000 else 5

def bar_at_or_before(bars,hm):
    ans=None
    for b in bars:
        if b["_dt"].strftime("%H:%M")>hm: break
        ans=b
    return ans

def percentile(value,vals):
    xs=sorted(x for x in vals if x is not None and math.isfinite(x))
    if not xs:return None
    return 100*sum(x<=value for x in xs)/len(xs)

def day_close(bars):
    return f(bars[-1],"close") if bars else None

def day_range_pct(bars):
    hs=[f(b,"high") for b in bars]; ls=[f(b,"low") for b in bars]
    hs=[x for x in hs if x is not None]; ls=[x for x in ls if x is not None]
    if not hs or not ls:return None
    c=day_close(bars)
    if not c:return None
    return (max(hs)-min(ls))/c*100

def day_turnover(bars):
    total=0.0
    for b in bars:
        c=f(b,"close"); v=f(b,"volume")
        if c is not None and v is not None: total+=c*v
    return total

def first30_volume(bars):
    return sum((f(b,"volume") or 0) for b in bars if "09:00"<=b["_dt"].strftime("%H:%M")<="09:25")

def prior_days(days,ad,n):
    xs=[d for d in sorted(days) if d<ad]
    return xs[-n:]

def market_snapshot(bysym,ad,hm="09:30"):
    vals=[]
    for sym,days in bysym.items():
        bars=days.get(ad)
        if not bars: continue
        b=bar_at_or_before(bars,hm)
        op=f(bars[0],"open"); cl=f(b or {},"close")
        if op and cl is not None:
            vals.append((sym,(cl/op-1)*100))
    if not vals:return {}
    rets=[x[1] for x in vals]
    med=statistics.median(rets)
    return {"breadth":100*sum(x>0 for x in rets)/len(rets),"median":med,"rets":dict(vals),"allrets":rets}

def platform_candidates(bars,start="09:30",end="11:00"):
    out=[]
    for i,b in enumerate(bars):
        hm=b["_dt"].strftime("%H:%M")
        if hm<start or hm>end or i<4: continue
        prior=bars[i-4:i]
        hs=[f(x,"high") for x in prior]; ls=[f(x,"low") for x in prior]
        if any(x is None for x in hs+ls): continue
        ph,pl=max(hs),min(ls); cc=f(b,"close"); cv=f(b,"volume") or 0
        if not cc: continue
        mid=(ph+pl)/2
        if not mid: continue
        width=(ph-pl)/mid*100
        pvs=[f(x,"volume") or 0 for x in prior]
        vr=cv/(statistics.median(pvs) or 1)
        risk=(cc-pl)/cc*100
        if width<=1.5 and cc>ph and vr>=1.5 and 1<=risk<=2.5:
            out.append((i,{"stop":pl,"volume_ratio":vr,"trigger_close":cc,"trigger_time":hm}))
    return out

def simulate(bars,entry_i,stop,target_r=2,cost_pct=.35,maxbars=24):
    if entry_i>=len(bars):return None
    op=f(bars[entry_i],"open")
    if op is None:return None
    entry=op+tick(op)
    if entry>=100 or stop>=entry:return None
    risk=entry-stop; rp=risk/entry*100
    if not (1<=rp<=2.5):return None
    target=entry+target_r*risk
    end=min(len(bars)-1,entry_i+maxbars)
    px=f(bars[end],"close"); reason="TIME"
    for j in range(entry_i,end+1):
        hi,lo=f(bars[j],"high"),f(bars[j],"low")
        if hi is None or lo is None: continue
        sh=lo<=stop; th=hi>=target
        if sh and th: px=stop; reason="STOP_AMBIGUOUS"; break
        if sh: px=stop; reason="STOP"; break
        if th: px=target; reason="TP2R"; break
    gross=(px-entry)/risk
    return {"entry":entry,"stop":stop,"target":target,"risk_pct":rp,"gross_r":gross,"net_r":gross-cost_pct/rp,"exit_reason":reason}

def features_for(bysym,sym,ad,market):
    days=bysym[sym]; bars=days.get(ad)
    if not bars:return None
    prev=prior_days(days,ad,10)
    if len(prev)<10:return None
    op=f(bars[0],"open"); prev_close=day_close(days[prev[-1]])
    b930=bar_at_or_before(bars,"09:30"); cl930=f(b930 or {},"close")
    if not op or not prev_close or cl930 is None:return None
    stock_ret=(cl930/op-1)*100
    rs=stock_ret-market["median"]
    pct=percentile(stock_ret,market["allrets"])
    gap=(op/prev_close-1)*100
    vols=[first30_volume(days[d]) for d in prev]
    abv=first30_volume(bars)/(statistics.median(vols) or 1)
    p5=prev[-5:]
    c5=day_close(days[p5[0]]); c1=day_close(days[prev[-1]])
    mom5=(c1/c5-1)*100 if c5 and c1 else None
    r3=[day_range_pct(days[d]) for d in prev[-3:]]
    r10=[day_range_pct(days[d]) for d in prev]
    r3=[x for x in r3 if x is not None]; r10=[x for x in r10 if x is not None]
    contract=(statistics.median(r3)/statistics.median(r10)) if r3 and r10 and statistics.median(r10) else None
    turns=[day_turnover(days[d]) for d in prev]
    liq=statistics.median(turns) if turns else None
    return {
        "breadth_0930":market["breadth"],"rs_0930":rs,"peer_pct_0930":pct,
        "abnormal_volume_30m":abv,"momentum_5d_pct":mom5,
        "contraction_ratio":contract,"gap_pct":gap,"turnover_10d_median":liq,
        "stock_ret_0930":stock_ret
    }

def qualifies(name,ft,sig=None):
    if not ft:return False
    base=(ft["breadth_0930"]>=55 and ft["rs_0930"]>0 and ft["peer_pct_0930"]>=80 and
          ft["abnormal_volume_30m"]>=1.5 and -1<=ft["gap_pct"]<=3 and
          ft["turnover_10d_median"]>=20_000_000)
    if not base:return False
    if name=="A1":return True
    if name=="A2":return ft["momentum_5d_pct"] is not None and ft["momentum_5d_pct"]>0
    if name=="A3":return ft["contraction_ratio"] is not None and ft["contraction_ratio"]<=.80
    if name=="A4":return ft["momentum_5d_pct"] is not None and ft["momentum_5d_pct"]>0 and ft["contraction_ratio"] is not None and ft["contraction_ratio"]<=.80
    if name=="A5":
        return ft["stock_ret_0930"]<=4 and ft["gap_pct"]<=2 and sig is not None and sig["volume_ratio"]<=4
    return False

def metrics(rows,cost=.35):
    if not rows:return {"n":0}
    xs=[float(r["gross_r"])-cost/float(r["risk_pct"]) for r in rows]
    gp=sum(x for x in xs if x>0); gl=-sum(x for x in xs if x<0)
    return {"n":len(xs),"win_rate":sum(x>0 for x in xs)/len(xs),"expectancy_r":statistics.mean(xs),"pf":gp/gl if gl else None}

def stable(rows):
    a=metrics(rows,.35); y25=metrics([r for r in rows if r["date"].startswith("2025")],.35); y26=metrics([r for r in rows if r["date"].startswith("2026")],.35); c45=metrics(rows,.45)
    ok=(a.get("n",0)>=100 and y25.get("n",0)>=30 and y26.get("n",0)>=30 and
        (a.get("expectancy_r") or -999)>0 and (a.get("pf") or 0)>1 and
        (y25.get("expectancy_r") or -999)>0 and (y25.get("pf") or 0)>1 and
        (y26.get("expectancy_r") or -999)>0 and (y26.get("pf") or 0)>1 and
        (c45.get("expectancy_r") or -999)>0)
    return ok,a,y25,y26

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",required=True)
    ap.add_argument("--out",default="research_output_stage7a")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    bysym={}
    for p in Path(args.data_dir).glob("*_5.json"):
        obj=json.loads(p.read_text(encoding="utf-8"))
        bysym[str(obj["symbol"])]=group_days(obj)
    all_dates=sorted({d for days in bysym.values() for d in days})
    groups={k:[] for k in ["A1","A2","A3","A4","A5"]}
    for ad in all_dates:
        market=market_snapshot(bysym,ad,"09:30")
        if not market: continue
        for sym,days in bysym.items():
            bars=days.get(ad)
            if not bars: continue
            ft=features_for(bysym,sym,ad,market)
            if not ft: continue
            cands=platform_candidates(bars)
            if not cands: continue
            for name in groups:
                chosen=None
                for i,sig in cands:
                    if not qualifies(name,ft,sig): continue
                    sim=simulate(bars,i+1,sig["stop"])
                    if sim:
                        chosen={"hypothesis":name,"symbol":sym,"date":str(ad),**ft,**sig,**sim}
                        break
                if chosen: groups[name].append(chosen)
    report={"scope":"Stage7A pre-registered broader market alpha","promotion_decision":"RESEARCH_ONLY","hypotheses":{}}
    allrows=[]
    for name,rows in groups.items():
        ok,a,y25,y26=stable(rows)
        report["hypotheses"][name]={
            "all":a,"2025":y25,"2026":y26,"stable_positive":ok,
            "cost_sensitivity":{"0.25":metrics(rows,.25),"0.35":metrics(rows,.35),"0.45":metrics(rows,.45)}
        }
        allrows.extend(rows)
    report["stable_positive_hypotheses"]=[k for k,v in report["hypotheses"].items() if v["stable_positive"]]
    report["limitations"]=[
        "Current-listed 100-name sample has survivorship bias.",
        "Peer percentile is cross-sectional proxy, not official sector strength.",
        "Thresholds are fixed in STAGE7A_PREREGISTRATION.md.",
        "Positive results remain research-only pending broader-universe OOS, walk-forward and leakage review."
    ]
    (out/"stage7a_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if allrows:
        fields=sorted({k for r in allrows for k in r})
        with (out/"stage7a_trades.csv").open("w",newline="",encoding="utf-8-sig") as fh:
            w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(allrows)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
