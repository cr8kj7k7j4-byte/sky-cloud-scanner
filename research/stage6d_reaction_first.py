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

def median(xs):
    xs=[x for x in xs if x is not None]
    return statistics.median(xs) if xs else None

def percentile(value, vals):
    xs=sorted(x for x in vals if x is not None and math.isfinite(x))
    if not xs:return None
    return 100*sum(x<=value for x in xs)/len(xs)

def bar_at_or_before(bars,hm):
    ans=None
    for b in bars:
        t=b["_dt"].strftime("%H:%M")
        if t>hm: break
        ans=b
    return ans

def reaction_snapshot(bysym,ad,sym,hm):
    day=bysym.get(sym,{}).get(ad)
    if not day:return None
    sb=bar_at_or_before(day,hm)
    so=f(day[0],"open"); sc=f(sb or {},"close")
    if not so or sc is None:return None
    sret=(sc/so-1)*100
    rets=[]
    for psym,days in bysym.items():
        pday=days.get(ad)
        if not pday: continue
        pb=bar_at_or_before(pday,hm)
        po=f(pday[0],"open"); pc=f(pb or {},"close")
        if po and pc is not None: rets.append((pc/po-1)*100)
    if not rets:return None
    med=statistics.median(rets)
    return {
        "stock_ret":sret,
        "breadth":100*sum(x>0 for x in rets)/len(rets),
        "median_ret":med,
        "rs":sret-med,
        "peer_pct":percentile(sret,rets),
    }

def medvol(bars,i,n=4):
    xs=[f(x,"volume") or 0 for x in bars[max(0,i-n):i]]
    return statistics.median(xs) if xs else 0

def simulate(bars,entry_i,stop,target_r=2,cost_pct=.35,maxbars=24):
    if entry_i>=len(bars): return None
    op=f(bars[entry_i],"open")
    if op is None:return None
    entry=op+tick(op)
    if entry>=100 or stop>=entry:return None
    risk=entry-stop; risk_pct=risk/entry*100
    if not (1<=risk_pct<=2.5): return None
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
    return {
        "entry":entry,"stop":stop,"target":target,"risk_pct":risk_pct,
        "gross_r":gross,"net_r":gross-cost_pct/risk_pct,"exit_reason":reason
    }

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
        vr=cv/(medvol(bars,i) or 1)
        risk=(cc-pl)/cc*100
        if width<=1.5 and cc>ph and vr>=1.5 and 1<=risk<=2.5:
            out.append((i,{"stop":pl,"volume_ratio":vr,"trigger_close":cc,"trigger_time":hm}))
    return out

def first30_high(bars):
    xs=[f(b,"high") for b in bars if "09:00"<=b["_dt"].strftime("%H:%M")<="09:25"]
    xs=[x for x in xs if x is not None]
    return max(xs) if xs else None

def h1(bars,s20,s30,gap,anti=False):
    if not(s30 and s30["rs"]>0 and s30["peer_pct"]>=70 and s30["breadth"]>=50): return None
    if gap is None or gap<-1 or gap>3:return None
    for i,sig in platform_candidates(bars):
        trig_ret=(sig["trigger_close"]/f(bars[0],"open")-1)*100 if f(bars[0],"open") else None
        if anti and (sig["volume_ratio"]>4 or trig_ret is None or trig_ret>5): continue
        sim=simulate(bars,i+1,sig["stop"])
        if sim:return {**sig,**sim}
    return None

def h2(bars,s20,s30,gap):
    if not(s20 and s30):return None
    if not(s20["rs"]>0 and s30["rs"]>0 and s30["rs"]>=s20["rs"] and s30["peer_pct"]>=70 and s30["breadth"]>=50): return None
    if gap is None or gap<-1 or gap>3:return None
    return h1(bars,s20,s30,gap,anti=False)

def h3(bars,s20,s30,gap,anti=False):
    if not(s30 and s30["rs"]>0 and s30["peer_pct"]>=70):return None
    if gap is None or gap<-1 or gap>3:return None
    fh=first30_high(bars)
    if fh is None:return None
    broke=False; pull_start=None; pull_low=None
    for i,b in enumerate(bars):
        hm=b["_dt"].strftime("%H:%M")
        if hm<"09:30" or hm>"11:00": continue
        hi,lo,cc=f(b,"high"),f(b,"low"),f(b,"close")
        if None in (hi,lo,cc): continue
        if not broke:
            if hi>fh: broke=True
            continue
        if pull_start is None:
            if cc<=fh:
                pull_start=i; pull_low=lo
            continue
        pull_low=min(pull_low,lo)
        if cc>fh:
            vr=(f(b,"volume") or 0)/(medvol(bars,i) or 1)
            trig_ret=(cc/f(bars[0],"open")-1)*100 if f(bars[0],"open") else None
            if vr<1.5: continue
            if anti and (vr>4 or trig_ret is None or trig_ret>5): continue
            sim=simulate(bars,i+1,pull_low)
            if sim:return {"trigger_time":hm,"volume_ratio":vr,"trigger_close":cc,**sim}
    return None

def metrics(rows,cost_pct=.35):
    if not rows:return {"n":0}
    xs=[]
    for r in rows:
        gross=float(r["gross_r"]); rp=float(r["risk_pct"])
        xs.append(gross-cost_pct/rp)
    gp=sum(x for x in xs if x>0); gl=-sum(x for x in xs if x<0)
    return {
        "n":len(xs),"win_rate":sum(x>0 for x in xs)/len(xs),
        "expectancy_r":statistics.mean(xs),"pf":gp/gl if gl else None
    }

def stable(rows):
    a=metrics(rows,.35)
    y25=metrics([r for r in rows if str(r["action_date"]).startswith("2025")],.35)
    y26=metrics([r for r in rows if str(r["action_date"]).startswith("2026")],.35)
    ok=(a.get("n",0)>=30 and y25.get("n",0)>=10 and y26.get("n",0)>=10 and
        (a.get("expectancy_r") or -999)>0 and (a.get("pf") or 0)>1 and
        (y25.get("expectancy_r") or -999)>0 and (y25.get("pf") or 0)>1 and
        (y26.get("expectancy_r") or -999)>0 and (y26.get("pf") or 0)>1)
    return ok,a,y25,y26

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--events",required=True)
    ap.add_argument("--data-dir",required=True)
    ap.add_argument("--out",default="research_output_stage6d")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    with open(args.events,encoding="utf-8-sig",newline="") as fh:
        events=list(csv.DictReader(fh))
    bysym={}
    for p in Path(args.data_dir).glob("*_5.json"):
        obj=json.loads(p.read_text(encoding="utf-8"))
        bysym[str(obj["symbol"])]=group_days(obj)

    groups={k:[] for k in ["H1_DELAYED","H2_RS_PERSIST","H3_RECLAIM","H1_ANTI","H3_ANTI"]}
    seen=set()
    for e in events:
        sym=str(e["symbol"])
        qd=datetime.fromisoformat(e["query_date"]).date()
        days=bysym.get(sym)
        if not days: continue
        try:t=int("".join(ch for ch in str(e.get("announce_time","")) if ch.isdigit())[:4] or "9999")
        except:t=9999
        ad=qd if qd in days and t<=830 else next((d for d in sorted(days) if d>qd),None)
        if ad is None:continue
        key=(sym,str(ad),e.get("subject",""))
        if key in seen:continue
        seen.add(key)
        bars=days[ad]
        prev=[d for d in sorted(days) if d<ad]
        if not prev:continue
        pc=f(days[prev[-1]][-1],"close"); op=f(bars[0],"open")
        if not pc or not op:continue
        gap=(op/pc-1)*100
        s20=reaction_snapshot(bysym,ad,sym,"09:20")
        s30=reaction_snapshot(bysym,ad,sym,"09:30")
        tests=[
            ("H1_DELAYED",h1(bars,s20,s30,gap,False)),
            ("H2_RS_PERSIST",h2(bars,s20,s30,gap)),
            ("H3_RECLAIM",h3(bars,s20,s30,gap,False)),
            ("H1_ANTI",h1(bars,s20,s30,gap,True)),
            ("H3_ANTI",h3(bars,s20,s30,gap,True)),
        ]
        for name,res in tests:
            if res:
                groups[name].append({
                    "hypothesis":name,"symbol":sym,"action_date":str(ad),"gap_pct":gap,
                    "rs_0920":None if not s20 else s20["rs"],
                    "rs_0930":None if not s30 else s30["rs"],
                    "peer_0930":None if not s30 else s30["peer_pct"],
                    "breadth_0930":None if not s30 else s30["breadth"],
                    **res
                })

    report={"scope":"Stage6D pre-registered reaction-first research","promotion_decision":"RESEARCH_ONLY","hypotheses":{}}
    allrows=[]
    for name,rows in groups.items():
        ok,a,y25,y26=stable(rows)
        report["hypotheses"][name]={
            "all":a,"2025":y25,"2026":y26,"stable_positive":ok,
            "cost_sensitivity":{
                "0.25":metrics(rows,.25),"0.35":metrics(rows,.35),"0.45":metrics(rows,.45)
            }
        }
        allrows.extend(rows)
    report["stable_positive_hypotheses"]=[k for k,v in report["hypotheses"].items() if v["stable_positive"]]
    report["limitations"]=[
        "Pre-registered thresholds are fixed in STAGE6D_PREREGISTRATION.md.",
        "Current 100-symbol universe has survivorship bias.",
        "Peer percentile is a cross-sectional proxy, not official sector strength.",
        "Positive results remain research-only pending wider universe, separate OOS, walk-forward, leakage audit, and explicit approval."
    ]
    (out/"stage6d_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if allrows:
        fields=sorted({k for r in allrows for k in r})
        with (out/"stage6d_trades.csv").open("w",newline="",encoding="utf-8-sig") as fh:
            w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(allrows)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
