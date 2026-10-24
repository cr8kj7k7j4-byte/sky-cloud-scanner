from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path

COSTS=[0.00,0.10,0.20,0.25,0.35]
TOPKS=[1,3,5]
HORIZONS={"30m":6,"60m":12,"120m":24}
WARMUP=20

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"win_rate":sum(v>0 for v in vals)/len(vals),
            "expectancy_pct":statistics.mean(vals),"median_pct":statistics.median(vals),
            "pf":gp/gl if gl>0 else None}

def rank01(vals):
    n=len(vals)
    if n<=1:return [0.5]*n
    order=sorted(range(n),key=lambda i:vals[i])
    out=[0.0]*n
    for r,i in enumerate(order):out[i]=r/(n-1)
    return out

def load(path):
    syms={}
    for p in sorted(Path(path).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if not ds:continue
            d=datetime.fromisoformat(ds).date().isoformat()
            by[d].append(b)
        days={}
        for d,bars in by.items():
            bars.sort(key=lambda x:x["date"])
            if len(bars)<30:continue
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            days[d]={"bars":bars,"open":op,"close":cl}
        ds=sorted(days)
        hist_first6=deque(maxlen=WARMUP)
        prev_close=None
        for d in ds:
            r=days[d]; bars=r["bars"]
            vols=[fnum(x.get("volume")) or 0 for x in bars[:6]]
            v30=sum(vols)
            r["v30"]=v30
            r["prev_close"]=prev_close
            if len(hist_first6)>=WARMUP:
                med=statistics.median(hist_first6)
                r["baseline_v30"]=med if med>0 else None
            else:r["baseline_v30"]=None
            hist_first6.append(v30)
            prev_close=r["close"]
        syms[sym]={"exchange":o.get("exchange"),"days":days}
    return syms

def bar_vwap(bars):
    vols=[]; pxs=[]
    for b in bars:
        v=fnum(b.get("volume")) or 0
        p=fnum(b.get("average"))
        if p is None:p=fnum(b.get("close"))
        vols.append(v);pxs.append(p)
    den=sum(vols)
    if den<=0:return None
    return sum(v*p for v,p in zip(vols,pxs) if p is not None)/den

def detect_events(syms):
    bydate=defaultdict(list)
    for sym,obj in syms.items():
        for d,r in obj["days"].items():
            bars=r["bars"]; prev_close=r.get("prev_close"); base=r.get("baseline_v30")
            if prev_close is None or base is None:continue
            # Search 09:15~10:30 for first valid event.
            cum=[]
            event=None
            for i,b in enumerate(bars):
                if i<3 or i>18:continue
                cum=bars[:i+1]
                c=fnum(b.get("close")); h=fnum(b.get("high")); l=fnum(b.get("low"))
                if c is None or h is None or l is None:continue
                vwap=bar_vwap(cum)
                if vwap is None:continue
                vol=sum((fnum(x.get("volume")) or 0) for x in cum)
                # scale baseline proportionally to elapsed first-30m fraction; floor 1/6
                expected=base*max((i+1)/6,1/6)
                vol_abn=vol/expected if expected>0 else None
                ret=(c/prev_close-1)*100
                vdist=(c/vwap-1)*100
                # local breakout = close exceeds max prior 4 highs
                prior=cum[max(0,len(cum)-5):-1]
                if len(prior)<3:continue
                ph=max(fnum(x.get("high")) for x in prior if fnum(x.get("high")) is not None)
                pl=min(fnum(x.get("low")) for x in prior if fnum(x.get("low")) is not None)
                breakout=c>ph
                risk=(c-pl)/c*100 if c else None
                anti=ret<5 and vdist<2.5 and risk is not None and risk<=2.5
                accept=c>=vwap and ret>0
                trigger=vol_abn is not None and vol_abn>=1.5 and breakout and accept and anti
                if trigger and i+1<len(bars):
                    entry=fnum(bars[i+1].get("open"))
                    if entry is None or entry>100:continue
                    outs={}
                    for hn,off in HORIZONS.items():
                        j=i+1+off
                        if j<len(bars):
                            px=fnum(bars[j].get("close"))
                            if px is not None:outs[hn]=(px/entry-1)*100
                    if not outs:continue
                    event={"symbol":sym,"exchange":obj["exchange"],"date":d,"bar_index":i,
                           "trigger_time":b["date"],"entry":entry,"ret":ret,"vol_abn":vol_abn,
                           "vwap_dist":vdist,"risk_pct":risk,"range_width_pct":(ph-pl)/c*100 if c else None,
                           **outs}
                    break
            if event:bydate[d].append(event)

    rows=[]
    for d,arr in bydate.items():
        if len(arr)<2:continue
        feats=["ret","vol_abn","vwap_dist"]
        ranks={f:rank01([r[f] for r in arr]) for f in feats}
        for i,r in enumerate(arr):
            r["rank_ret"]=ranks["ret"][i]; r["rank_vol"]=ranks["vol_abn"][i]; r["rank_vwap"]=ranks["vwap_dist"][i]
            r["score"]=0.4*r["rank_ret"]+0.4*r["rank_vol"]+0.2*r["rank_vwap"]
            rows.append(r)
    return rows

def select(rows,k):
    by=defaultdict(list)
    for r in rows:by[r["date"]].append(r)
    out=[]
    for d,arr in by.items():
        arr=sorted(arr,key=lambda r:(r["score"],r["vol_abn"]),reverse=True)
        out.extend(arr[:k])
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_event_driven_rank")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    syms=load(args.history_dir)
    rows=detect_events(syms)
    splits={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["date"][:4])
        if y<=2024:splits["train"].append(r)
        elif y==2025:splits["valid"].append(r)
        elif y==2026:splits["test"].append(r)

    grid={}
    for k in TOPKS:
        grid[str(k)]={}
        for h in HORIZONS:
            grid[str(k)][h]={}
            for c in COSTS:
                ck=f"{c:.2f}";grid[str(k)][h][ck]={}
                for sp,arr in splits.items():
                    sel=select(arr,k)
                    vals=[r[h]-c for r in sel if h in r]
                    grid[str(k)][h][ck][sp]=metrics(vals)

    cand=[]
    for k in TOPKS:
        for h in HORIZONS:
            m=grid[str(k)][h]["0.20"]["train"]
            if m.get("n",0)>=100:
                cand.append((m.get("expectancy_pct",-999),m.get("pf") or 0,m.get("n",0),k,h))
    cand.sort(reverse=True)
    selected={"topk":None,"horizon":None}
    if cand:
        _,_,_,k,h=cand[0];selected={"topk":k,"horizon":h}

    promo=False;reasons=[]
    if selected["topk"] is not None:
        k,h=selected["topk"],selected["horizon"]
        vm=grid[str(k)][h]["0.20"]["valid"];tm=grid[str(k)][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=100 and tm.get("n",0)>=100 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)
        if not promo:reasons.append("Training-selected event-driven rank failed 2025+2026 promotion gate at 0.20% cost.")

    rep={"method":"Event-driven intraday opportunity ranking OOS",
         "trigger":"abnormal volume >=1.5x proportional baseline + local breakout + VWAP acceptance + anti-chase",
         "ranking":"40% momentum + 40% abnormal volume + 20% VWAP distance rank",
         "eligible_events":len(rows),"split_counts":{k:len(v) for k,v in splits.items()},
         "topks":TOPKS,"costs_pct":COSTS,
         "selection_rule":"Training only at 0.20%, n>=100.",
         "promotion_rule":"2025 and 2026 each n>=100, expectancy>0, PF>1.05 at 0.20%.",
         "selected":selected,"promotion_pass":promo,"reasons":reasons,"grid":grid,
         "limitations":["Current-universe sample has survivorship bias.","Ranking pool is fixed 100-stock sample.","Historical spread/limit-up unavailable."]}
    (out/"event_driven_rank_report.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Event-Driven Ranking OOS",f"- Eligible events: {len(rows)}",f"- Split counts: {rep['split_counts']}",
           f"- Selected: {selected}",f"- Promotion pass: **{promo}**"]
    if selected["topk"] is not None:
        k,h=selected["topk"],selected["horizon"]
        lines+=["","## Selected @0.20%"]
        for sp in ("train","valid","test"):
            m=grid[str(k)][h]["0.20"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"event_driven_rank_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
