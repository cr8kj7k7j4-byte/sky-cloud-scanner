from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path

COSTS=[0.00,0.10,0.20,0.25,0.35]
HORIZONS={"30m":6,"60m":12,"120m":24}
SLOTS=range(3,37,3)  # every 15m, starting ~09:15
LOOKBACK_DAYS=20

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

def quantile(xs,q):
    xs=sorted(x for x in xs if x is not None)
    if not xs:return None
    p=(len(xs)-1)*q
    lo=int(math.floor(p)); hi=int(math.ceil(p))
    if lo==hi:return xs[lo]
    w=p-lo
    return xs[lo]*(1-w)+xs[hi]*w

def load_history(path):
    syms={}
    for p in sorted(Path(path).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if not ds:continue
            d=datetime.fromisoformat(ds).date().isoformat()
            by[d].append(b)
        for d in by: by[d].sort(key=lambda x:x["date"])
        syms[sym]=by
    return syms

def safe_ret(a,b):
    return (a/b-1)*100 if a is not None and b not in (None,0) else None

def stdev_rets(closes):
    if len(closes)<4:return None
    rs=[]
    for i in range(1,len(closes)):
        if closes[i-1]: rs.append(closes[i]/closes[i-1]-1)
    return statistics.pstdev(rs)*100 if rs else None

def build_rows(syms):
    vol_hist=defaultdict(lambda:defaultdict(lambda:deque(maxlen=LOOKBACK_DAYS)))
    rows=[]
    dates=sorted({d for by in syms.values() for d in by})
    for d in dates:
        slot_rows=defaultdict(list)
        for sym,by in syms.items():
            bars=by.get(d)
            if not bars or len(bars)<30:continue
            closes=[fnum(b.get("close")) for b in bars]
            highs=[fnum(b.get("high")) for b in bars]
            lows=[fnum(b.get("low")) for b in bars]
            vols=[fnum(b.get("volume")) or 0 for b in bars]
            op=fnum(bars[0].get("open"))
            if op is None:continue
            for i in SLOTS:
                if i>=len(bars):continue
                c=closes[i]
                if c is None:continue
                start=max(0,i-5)
                c5=closes[i-1] if i>=1 else None
                c15=closes[i-3] if i>=3 else None
                c30=closes[i-6] if i>=6 else None
                mom5=safe_ret(c,c5); mom15=safe_ret(c,c15); mom30=safe_ret(c,c30)
                cum=bars[:i+1]
                den=sum((fnum(x.get("volume")) or 0) for x in cum)
                vwap=(sum((fnum(x.get("volume")) or 0)*(fnum(x.get("average")) if fnum(x.get("average")) is not None else fnum(x.get("close"))) for x in cum)/den) if den>0 else None
                vdist=safe_ret(c,vwap)
                hh=max(x for x in highs[:i+1] if x is not None); ll=min(x for x in lows[:i+1] if x is not None)
                rpos=(c-ll)/(hh-ll) if hh>ll else None
                drawdown=(c/hh-1)*100 if hh else None
                vol15=sum(vols[max(0,i-2):i+1])
                hist=vol_hist[sym][i]
                volratio=vol15/statistics.median(hist) if len(hist)>=LOOKBACK_DAYS and statistics.median(hist)>0 else None
                volat=stdev_rets([x for x in closes[max(0,i-5):i+1] if x is not None])
                entry=fnum(bars[i+1].get("open")) if i+1<len(bars) else None
                if entry is None or entry>100:continue
                outs={}
                for h,off in HORIZONS.items():
                    j=i+1+off
                    if j<len(bars):
                        px=closes[j]
                        if px is not None:outs[h]=(px/entry-1)*100
                if not outs:continue
                slot_rows[i].append({
                    "symbol":sym,"date":d,"slot":i,"entry":entry,
                    "mom5":mom5,"mom15":mom15,"mom30":mom30,
                    "vwap_dist":vdist,"range_pos":rpos,"drawdown":drawdown,
                    "vol_ratio":volratio,"volatility":volat,**outs
                })
        # add cross-sectional features using only current/past data
        for i,arr in slot_rows.items():
            eligible=[r for r in arr if all(r.get(k) is not None for k in ("mom15","vwap_dist","range_pos","vol_ratio","volatility"))]
            if len(eligible)>=20:
                med=statistics.median(r["mom15"] for r in eligible)
                breadth=sum(r["mom15"]>0 for r in eligible)/len(eligible)
                vals=sorted(r["mom15"] for r in eligible)
                for r in eligible:
                    rank=sum(v<=r["mom15"] for v in vals)/len(vals)
                    r["rs_rank"]=rank
                    r["market_breadth"]=breadth
                    r["market_median_mom15"]=med
                    rows.append(r)
        # update same-slot volume history AFTER snapshots for the day
        for sym,by in syms.items():
            bars=by.get(d)
            if not bars:continue
            vols=[fnum(b.get("volume")) or 0 for b in bars]
            for i in SLOTS:
                if i<len(bars):
                    vol_hist[sym][i].append(sum(vols[max(0,i-2):i+1]))
    return rows

FEATURES=["mom5","mom15","mom30","vwap_dist","range_pos","drawdown","vol_ratio","volatility","rs_rank","market_breadth"]

def make_thresholds(train):
    qs=[0.1,0.2,0.8,0.9]
    return {f:{str(q):quantile([r[f] for r in train if r.get(f) is not None],q) for q in qs} for f in FEATURES}

def states_for(r,thr):
    s=[]
    for f in FEATURES:
        x=r.get(f)
        if x is None:continue
        t=thr[f]
        if t["0.9"] is not None and x>=t["0.9"]:s.append(f+"__P90")
        if t["0.8"] is not None and x>=t["0.8"]:s.append(f+"__P80")
        if t["0.2"] is not None and x<=t["0.2"]:s.append(f+"__P20")
        if t["0.1"] is not None and x<=t["0.1"]:s.append(f+"__P10")
    # small, predeclared interaction set
    if r.get("rs_rank",0)>=thr["rs_rank"]["0.8"] and r.get("vol_ratio",0)>=thr["vol_ratio"]["0.8"]:
        s.append("RS80_VOL80")
    if r.get("mom15",0)>=thr["mom15"]["0.8"] and r.get("range_pos",0)>=thr["range_pos"]["0.8"]:
        s.append("MOM80_POS80")
    if r.get("vwap_dist",0)>=thr["vwap_dist"]["0.8"] and r.get("rs_rank",0)>=thr["rs_rank"]["0.8"]:
        s.append("VWAP80_RS80")
    if r.get("market_breadth",0)>=thr["market_breadth"]["0.8"] and r.get("rs_rank",0)>=thr["rs_rank"]["0.8"]:
        s.append("BREADTH80_RS80")
    return s

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_feature_states")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=build_rows(load_history(args.history_dir))
    splits={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["date"][:4])
        if y<=2024:splits["train"].append(r)
        elif y==2025:splits["valid"].append(r)
        elif y==2026:splits["test"].append(r)
    thr=make_thresholds(splits["train"])
    for arr in splits.values():
        for r in arr:r["states"]=states_for(r,thr)

    all_states=sorted({s for r in splits["train"] for s in r["states"]})
    grid={}
    for st in all_states:
        grid[st]={}
        for h in HORIZONS:
            grid[st][h]={}
            for c in COSTS:
                ck=f"{c:.2f}";grid[st][h][ck]={}
                for sp,arr in splits.items():
                    vals=[r[h]-c for r in arr if st in r["states"] and h in r]
                    grid[st][h][ck][sp]=metrics(vals)

    cand=[]
    for st in all_states:
        for h in HORIZONS:
            m=grid[st][h]["0.20"]["train"]
            if m.get("n",0)>=300 and (m.get("expectancy_pct") or -999)>0:
                cand.append((m.get("expectancy_pct"),m.get("pf") or 0,m.get("n",0),st,h))
    cand.sort(reverse=True)
    selected={"state":None,"horizon":None}
    if cand:
        _,_,_,st,h=cand[0];selected={"state":st,"horizon":h}

    promo=False
    if selected["state"]:
        st,h=selected["state"],selected["horizon"]
        vm=grid[st][h]["0.20"]["valid"];tm=grid[st][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=200 and tm.get("n",0)>=200 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)

    rep={"method":"P0-F interpretable 5m state discovery",
         "snapshot_frequency":"every 15m from ~09:15",
         "features":FEATURES,
         "thresholds":"Train-only deciles/quintiles applied unchanged to 2025/2026",
         "eligible_rows":len(rows),"split_counts":{k:len(v) for k,v in splits.items()},
         "state_count":len(all_states),"costs_pct":COSTS,
         "selection_rule":"Train-only, 0.20% cost, state n>=300, positive expectancy; choose best expectancy.",
         "promotion_rule":"2025 and 2026 each n>=200, expectancy>0, PF>1.05 at 0.20%.",
         "selected":selected,"promotion_pass":promo,"train_thresholds":thr,"grid":grid,
         "limitations":["Current-universe survivorship bias.","Fixed 100-stock sample, not full market.","Multiple-state exploration remains research-only; no production promotion without OOS pass.","Historical spread/limit-up unavailable."]}
    (out/"feature_state_report.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky P0-F Feature State Discovery",f"- Eligible rows: {len(rows)}",f"- Split counts: {rep['split_counts']}",
           f"- States tested: {len(all_states)}",f"- Selected: {selected}",f"- Promotion pass: **{promo}**"]
    if selected["state"]:
        st,h=selected["state"],selected["horizon"]
        lines+=["","## Selected @0.20%"]
        for sp in ("train","valid","test"):
            m=grid[st][h]["0.20"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    else:
        lines+=["","- No train state met positive expectancy with n>=300 at 0.20% cost."]
    (out/"feature_state_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
