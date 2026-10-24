from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import defaultdict,deque
from datetime import datetime
from pathlib import Path

COSTS=[0.00,0.10,0.20,0.25,0.35]
TOPKS=[3,5,10]
HORIZONS={"60m":11,"120m":23,"close":None}
WARMUP_DAYS=20

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def pct_rank(vals):
    pairs=sorted((v,i) for i,v in enumerate(vals))
    n=len(vals); out=[0.5]*n
    if n<=1:return out
    for rank,(_,i) in enumerate(pairs):
        out[i]=rank/(n-1)
    return out

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    return {
      "n":len(vals),
      "win_rate":sum(v>0 for v in vals)/len(vals),
      "expectancy_pct":statistics.mean(vals),
      "median_pct":statistics.median(vals),
      "pf":gp/gl if gl>0 else None,
    }

def load_history(path):
    syms={}
    for p in sorted(Path(path).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); ex=o.get("exchange"); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if not ds:continue
            d=datetime.fromisoformat(ds).date().isoformat()
            by[d].append(b)
        days={}
        for d,bars in by.items():
            bars.sort(key=lambda z:z["date"])
            if len(bars)<12:continue
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            first6=bars[:6]
            c30=fnum(first6[-1].get("close"))
            vols=[fnum(x.get("volume")) or 0 for x in first6]
            v30=sum(vols)
            avgs=[]
            for x in first6:
                a=fnum(x.get("average"))
                if a is None:a=fnum(x.get("close"))
                avgs.append(a)
            den=sum(vols)
            vwap=sum(v*a for v,a in zip(vols,avgs) if a is not None)/den if den>0 else None
            hi=max(fnum(x.get("high")) for x in first6 if fnum(x.get("high")) is not None)
            lo=min(fnum(x.get("low")) for x in first6 if fnum(x.get("low")) is not None)
            ret30=(c30/op-1)*100 if op and c30 is not None else None
            vwap_dist=(c30/vwap-1)*100 if vwap and c30 is not None else None
            range_pos=(c30-lo)/(hi-lo) if c30 is not None and hi>lo else None
            entry=fnum(bars[6].get("open")) if len(bars)>6 else None
            if entry is None:continue
            out={}
            for h,idx in HORIZONS.items():
                px=fnum(bars[-1].get("close")) if idx is None else (fnum(bars[idx].get("close")) if len(bars)>idx else None)
                if px is not None:out[h]=(px/entry-1)*100
            days[d]={
              "bars":bars,"open":op,"close":cl,"entry":entry,"ret30":ret30,"v30":v30,
              "vwap_dist":vwap_dist,"range_pos":range_pos,**out
            }
        ds=sorted(days)
        hist_v=deque(maxlen=WARMUP_DAYS)
        prev_close=None; prev_ret=None
        for d in ds:
            r=days[d]
            r["prev_close"]=prev_close
            r["prev_day_ret"]=prev_ret
            if len(hist_v)>=WARMUP_DAYS:
                med=statistics.median(hist_v)
                r["vol_abn"]=r["v30"]/med if med>0 else None
            else:r["vol_abn"]=None
            hist_v.append(r["v30"])
            prev_close=r["close"]
            prev_ret=(r["close"]/r["open"]-1)*100 if r["open"] else None
        syms[sym]={"exchange":ex,"days":days}
    return syms

def build_rows(syms):
    bydate=defaultdict(list)
    for sym,obj in syms.items():
        for d,r in obj["days"].items():
            if r["entry"]>100:continue
            if r.get("ret30") is None or r.get("vol_abn") is None or r.get("vwap_dist") is None or r.get("range_pos") is None:continue
            if r.get("prev_day_ret") is None:continue
            bydate[d].append({
              "symbol":sym,"exchange":obj["exchange"],"date":d,"entry":r["entry"],
              "ret30":r["ret30"],"vol_abn":r["vol_abn"],"vwap_dist":r["vwap_dist"],
              "range_pos":r["range_pos"],"prev_day_ret":r["prev_day_ret"],
              **{h:r[h] for h in HORIZONS if h in r}
            })
    rows=[]
    for d,arr in bydate.items():
        if len(arr)<20:continue
        feats=["ret30","vol_abn","vwap_dist","range_pos","prev_day_ret"]
        ranks={f:pct_rank([r[f] for r in arr]) for f in feats}
        medret=statistics.median(r["ret30"] for r in arr)
        adv=sum(r["ret30"]>0 for r in arr)/len(arr)
        riskoff=(adv<0.40 and medret<0)
        for i,r in enumerate(arr):
            r["market_adv30"]=adv; r["market_medret30"]=medret; r["riskoff30"]=riskoff
            r["rank_mom"]=ranks["ret30"][i]
            r["rank_vol"]=ranks["vol_abn"][i]
            r["rank_vwap"]=ranks["vwap_dist"][i]
            r["rank_pos"]=ranks["range_pos"][i]
            r["rank_persist"]=ranks["prev_day_ret"][i]
            r["score_core"]=0.30*r["rank_mom"]+0.30*r["rank_vol"]+0.20*r["rank_vwap"]+0.20*r["rank_pos"]
            r["score_persist"]=0.25*r["rank_mom"]+0.25*r["rank_vol"]+0.20*r["rank_vwap"]+0.15*r["rank_pos"]+0.15*r["rank_persist"]
            r["anti_chase"]=not (r["ret30"]>=4 or r["vwap_dist"]>=2.5 or (r["ret30"]>=3 and r["range_pos"]>=0.95))
            rows.append(r)
    return rows

def select_daily(rows,variant,k):
    by=defaultdict(list)
    for r in rows:
        if variant.endswith("_NR") and r["riskoff30"]:continue
        if variant.endswith("_AC") and not r["anti_chase"]:continue
        score=r["score_persist"] if "PERSIST" in variant else r["score_core"]
        by[r["date"]].append((score,r))
    out=[]
    for d,arr in by.items():
        arr.sort(key=lambda x:(x[0],x[1]["vol_abn"]),reverse=True)
        out += [r for _,r in arr[:k]]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_rank_oos")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    syms=load_history(args.history_dir)
    rows=build_rows(syms)
    splits={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["date"][:4])
        if y<=2024:splits["train"].append(r)
        elif y==2025:splits["valid"].append(r)
        elif y==2026:splits["test"].append(r)

    variants=["CORE","CORE_NR","CORE_AC","PERSIST","PERSIST_NR","PERSIST_AC"]
    grid={}
    for v in variants:
        grid[v]={}
        for k in TOPKS:
            grid[v][str(k)]={}
            for h in HORIZONS:
                grid[v][str(k)][h]={}
                for c in COSTS:
                    ck=f"{c:.2f}";grid[v][str(k)][h][ck]={}
                    for sp,arr in splits.items():
                        sel=select_daily(arr,v,k)
                        vals=[r[h]-c for r in sel if h in r]
                        grid[v][str(k)][h][ck][sp]=metrics(vals)

    candidates=[]
    for v in variants:
        for k in TOPKS:
            for h in HORIZONS:
                m=grid[v][str(k)][h]["0.20"]["train"]
                if m.get("n",0)>=100:
                    candidates.append((m.get("expectancy_pct",-999),m.get("pf") or 0,m.get("n",0),v,k,h))
    candidates.sort(reverse=True)
    selected={"variant":None,"topk":None,"horizon":None}
    if candidates:
        _,_,_,v,k,h=candidates[0];selected={"variant":v,"topk":k,"horizon":h}

    promo=False;reasons=[]
    if selected["variant"]:
        v,k,h=selected["variant"],selected["topk"],selected["horizon"]
        vm=grid[v][str(k)][h]["0.20"]["valid"];tm=grid[v][str(k)][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=100 and tm.get("n",0)>=100 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)
        if not promo:reasons.append("Training-selected ranking strategy failed 2025+2026 promotion gate at 0.20% cost.")

    report={
      "method":"Cross-sectional intraday opportunity ranking OOS",
      "universe":"fixed deterministic 100-stock historical sample, entry<=100",
      "features":["first30m momentum rank","first30m abnormal volume rank","VWAP acceptance rank","opening range position rank","prior-day persistence rank"],
      "entry_rule":"rank after first 30m; enter next 5m bar open",
      "eligible_rows":len(rows),"split_counts":{k:len(v) for k,v in splits.items()},
      "variants":variants,"topks":TOPKS,"costs_pct":COSTS,
      "selection_rule":"Training only at 0.20%, n>=100; validation/test untouched for selection.",
      "promotion_rule":"2025 and 2026 each n>=100, expectancy>0, PF>1.05 at 0.20%.",
      "selected":selected,"promotion_pass":promo,"reasons":reasons,"grid":grid,
      "limitations":["Current-universe sample has survivorship bias.",
                     "Ranking universe is the fixed 100-stock sample, not full market.",
                     "Historical spread and exact limit-up state unavailable."]
    }
    (out/"rank_oos_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky P0-O Intraday Ranking OOS",f"- Eligible rows: {len(rows)}",f"- Split counts: {report['split_counts']}",
           f"- Selected: {selected}",f"- Promotion pass: **{promo}**"]
    if selected["variant"]:
        v,k,h=selected["variant"],selected["topk"],selected["horizon"]
        lines+=["","## Selected @0.20%"]
        for sp in ("train","valid","test"):
            m=grid[v][str(k)][h]["0.20"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"rank_oos_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
