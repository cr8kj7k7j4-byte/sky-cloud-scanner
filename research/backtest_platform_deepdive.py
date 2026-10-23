
from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

TARGETS=(1.5,2.0)
COSTS=(0.00,0.05,0.10,0.15,0.20,0.25,0.35,0.45,0.55)
MIN_RISK_PCT=0.30
MAX_RISK_PCT=2.50
MAX_HOLD_BARS=24

def dt(s): return datetime.fromisoformat(s)
def fv(x,k):
    v=x.get(k)
    return None if v in (None,"") else float(v)

def median(xs):
    xs=sorted(xs)
    if not xs: return None
    n=len(xs)
    return xs[n//2] if n%2 else (xs[n//2-1]+xs[n//2])/2

def group_day(data):
    out=defaultdict(list)
    for b in data:
        x={**b,"_dt":dt(b["date"])}
        out[x["_dt"].date()].append(x)
    for d in out: out[d].sort(key=lambda x:x["_dt"])
    return out

def prev_close_map(by):
    ds=sorted(by); out={}
    for i,d in enumerate(ds):
        out[d]=None if i==0 or not by[ds[i-1]] else fv(by[ds[i-1]][-1],"close")
    return out

def detect_platform(bars,i,pc):
    if i<4: return None
    prior=bars[i-4:i]; cur=bars[i]
    highs=[fv(x,"high") for x in prior]
    lows=[fv(x,"low") for x in prior]
    vols=[fv(x,"volume") or 0 for x in prior]
    if any(x is None for x in highs+lows): return None
    ph,pl=max(highs),min(lows)
    mid=(ph+pl)/2
    width=(ph-pl)/mid*100 if mid else 999
    cc=fv(cur,"close"); co=fv(cur,"open"); ch=fv(cur,"high"); cl=fv(cur,"low")
    cv=fv(cur,"volume") or 0
    avg=fv(cur,"average")
    medvol=median(vols) or 0
    volume_ratio=cv/medvol if medvol>0 else None
    if width>1.5 or cc is None or cc<=ph or volume_ratio is None or volume_ratio<=1.5:
        return None

    risk_pct=(cc-pl)/cc*100
    if not (MIN_RISK_PCT<=risk_pct<=MAX_RISK_PCT): return None

    breakout_pct=(cc/ph-1)*100
    vwap_dist=(cc/avg-1)*100 if avg else None
    candle_range_pct=(ch-cl)/cc*100 if None not in (ch,cl) and cc else None
    body_pct=abs(cc-co)/cc*100 if co is not None and cc else None
    close_pos=(cc-cl)/(ch-cl) if None not in (ch,cl) and ch>cl else None
    change_pct=(cc/pc-1)*100 if pc else None

    return {
        "entry":cc,"stop":pl,"risk_pct":risk_pct,
        "platform_width_pct":width,
        "breakout_pct":breakout_pct,
        "volume_ratio":volume_ratio,
        "vwap_distance_pct":vwap_dist,
        "candle_range_pct":candle_range_pct,
        "body_pct":body_pct,
        "close_pos":close_pos,
        "change_pct":change_pct,
    }

def simulate(bars,i,sig,target_r):
    e=sig["entry"]; s=sig["stop"]; risk=e-s; target=e+risk*target_r
    end=min(len(bars)-1,i+MAX_HOLD_BARS)
    exit_px=fv(bars[end],"close"); reason="TIME"; exit_i=end
    mfe=-999; mae=999
    for j in range(i+1,end+1):
        hi=fv(bars[j],"high"); lo=fv(bars[j],"low")
        if hi is None or lo is None: continue
        mfe=max(mfe,(hi-e)/risk); mae=min(mae,(lo-e)/risk)
        stop_hit=lo<=s; tp_hit=hi>=target
        if stop_hit and tp_hit:
            exit_px=s; reason="STOP_AMBIGUOUS"; exit_i=j; break
        if stop_hit:
            exit_px=s; reason="STOP"; exit_i=j; break
        if tp_hit:
            exit_px=target; reason=f"TP_{target_r}R"; exit_i=j; break
    return {
        "target_r":target_r,"gross_r":(exit_px-e)/risk,
        "exit_reason":reason,"bars_held":exit_i-i,
        "mfe_r":None if mfe==-999 else mfe,
        "mae_r":None if mae==999 else mae,
    }

def time_bucket(t):
    hh,mm=map(int,t.split(":")); m=hh*60+mm
    if m<=9*60+45: return "09:05-09:45"
    if m<=10*60+30: return "09:50-10:30"
    if m<=11*60+30: return "10:35-11:30"
    if m<=12*60+30: return "11:35-12:30"
    return "12:35-13:30"

def bucket(v, edges, labels):
    if v is None: return "NA"
    for lo,hi,label in zip(edges[:-1],edges[1:],labels):
        if lo<=v<hi: return label
    return labels[-1]

def scan_file(path):
    obj=json.loads(path.read_text(encoding="utf-8"))
    by=group_day(obj["data"]); pc=prev_close_map(by)
    rows=[]
    for d,bars in by.items():
        if not pc[d]: continue
        used=False
        for i in range(4,len(bars)):
            if used: break  # first qualifying platform breakout per symbol/day
            sig=detect_platform(bars,i,pc[d])
            if not sig or sig["entry"]>100 or (sig["change_pct"] or 0)<=0: continue
            t=bars[i]["_dt"].strftime("%H:%M")
            base={
                "symbol":obj["symbol"],"exchange":obj.get("exchange"),"date":str(d),
                "year":str(d)[:4],"trigger_time":t,"time_bucket":time_bucket(t),**sig
            }
            base["change_bucket"]=bucket(sig["change_pct"],[0,2,4,6,8,999],["0-2%","2-4%","4-6%","6-8%","8%+"])
            base["risk_bucket"]=bucket(sig["risk_pct"],[.3,.6,1.0,1.5,2.5001],["0.3-0.6%","0.6-1.0%","1.0-1.5%","1.5-2.5%"])
            base["volume_bucket"]=bucket(sig["volume_ratio"],[1.5,2,3,5,999],["1.5-2x","2-3x","3-5x","5x+"])
            base["vwap_bucket"]=bucket(sig["vwap_distance_pct"],[-999,0,.5,1,2,999],["<0%","0-0.5%","0.5-1%","1-2%","2%+"])
            base["width_bucket"]=bucket(sig["platform_width_pct"],[0,.5,1,1.5,999],["0-0.5%","0.5-1%","1-1.5%","1.5%+"])
            base["breakout_bucket"]=bucket(sig["breakout_pct"],[0,.2,.5,1,999],["0-0.2%","0.2-0.5%","0.5-1%","1%+"])
            for tr in TARGETS:
                rows.append({**base,**simulate(bars,i,sig,tr)})
            used=True
    return rows

def calc(rows,cost):
    if not rows:return {"n":0}
    vals=[r["gross_r"]-cost/r["risk_pct"] for r in rows]
    w=[x for x in vals if x>0]; l=[x for x in vals if x<0]
    gp=sum(w); gl=-sum(l)
    return {"n":len(vals),"expectancy_r":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(x>0 for x in vals)/len(vals)}

def segment(rows, dims, target_r, min_n=100):
    rs=[r for r in rows if r["target_r"]==target_r]
    groups=defaultdict(list)
    for r in rs:
        key=tuple(r[d] for d in dims); groups[key].append(r)
    out=[]
    for key,g in groups.items():
        if len(g)<min_n: continue
        rec={"target_r":target_r,"dims":"+".join(dims)}
        rec.update({d:v for d,v in zip(dims,key)})
        for c in COSTS:
            m=calc(g,c)
            rec[f"expR_cost_{c:.2f}"]=m["expectancy_r"]
            rec[f"PF_cost_{c:.2f}"]=m["pf"]
            rec[f"win_cost_{c:.2f}"]=m["win_rate"]
        rec["n"]=len(g)
        # Break-even round-trip cost, if gross edge is positive.
        mean_inv_risk=statistics.mean([1/r["risk_pct"] for r in g])
        gross=statistics.mean([r["gross_r"] for r in g])
        rec["gross_expR"]=gross
        rec["break_even_cost_pct"]=gross/mean_inv_risk if gross>0 and mean_inv_risk>0 else 0.0
        out.append(rec)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",default="research_data/history")
    ap.add_argument("--out",default="research_output_platform")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    rows=[]
    for p in sorted(Path(args.data_dir).glob("*_5.json")):
        rows.extend(scan_file(p))

    dims_list=[
        ["time_bucket"],["change_bucket"],["risk_bucket"],["volume_bucket"],
        ["vwap_bucket"],["width_bucket"],["breakout_bucket"],
        ["time_bucket","change_bucket"],["time_bucket","risk_bucket"],
        ["change_bucket","risk_bucket"],["volume_bucket","risk_bucket"],
        ["vwap_bucket","risk_bucket"],["width_bucket","volume_bucket"],
        ["breakout_bucket","volume_bucket"],
        ["time_bucket","change_bucket","risk_bucket"],
    ]
    segs=[]
    for tr in TARGETS:
        for dims in dims_list:
            segs.extend(segment(rows,dims,tr,100))

    # Conservative candidate rule: n>=200 and positive at 0.25% and 0.35%, PF>1.05 both.
    candidates=[]
    for s in segs:
        if s["n"]>=200 and s["expR_cost_0.25"]>0 and s["PF_cost_0.25"]>1.05 and \
           s["expR_cost_0.35"]>0 and s["PF_cost_0.35"]>1.05:
            candidates.append(s)
    candidates=sorted(candidates,key=lambda x:(x["expR_cost_0.35"],x["n"]),reverse=True)

    report={
        "scope":"Platform Breakout feature deep dive; deterministic 100-symbol research sample.",
        "targets":TARGETS,"costs_pct":COSTS,"trade_rows":len(rows),
        "candidate_rule":"n>=200; expectancy>0 and PF>1.05 at both 0.25% and 0.35% cost.",
        "promotion_candidates":candidates[:30],
        "verdict":"PASS_TO_OOS" if candidates else "NO_ROBUST_PLATFORM_SUBSEGMENT",
        "limitations":[
            "Uses current listing universe backward; survivorship bias remains.",
            "First qualifying platform breakout per symbol/day only.",
            "5m OHLC intrabar ambiguity is treated stop-first.",
            "Cost values are sensitivity assumptions, not the user's broker-specific actual cost.",
            "No production rule is changed by this research."
        ]
    }
    (out/"platform_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    if rows:
        fields=sorted({k for r in rows for k in r})
        with (out/"platform_trades.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    if segs:
        fields=sorted({k for r in segs for k in r})
        with (out/"platform_segments.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(segs)

    lines=[
        "# Sky Platform Breakout Deep Dive",
        f"- Verdict: **{report['verdict']}**",
        f"- Trade-path rows: {len(rows)}",
        f"- Robust candidates: {len(candidates)}",
        "",
        "Candidate threshold: n>=200 and positive expectancy/PF>1.05 at both 0.25% and 0.35% round-trip cost.",
        "",
        "## Limits",
        "- Research only; no production change.",
        "- Actual broker cost must be confirmed before any promotion.",
        "- Survivorship bias remains."
    ]
    (out/"platform_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
