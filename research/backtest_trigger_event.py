
from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path

COST_PCT = 0.45
MIN_RISK_PCT = 0.30
MAX_RISK_PCT = 2.50
MAX_HOLD_BARS = 24  # 120 minutes

def dt(s): return datetime.fromisoformat(s)

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
        out[d]=None if i==0 or not by[ds[i-1]] else float(by[ds[i-1]][-1]["close"])
    return out

def f(x, k):
    v=x.get(k)
    return None if v in (None,"") else float(v)

def med(xs):
    xs=sorted(xs); n=len(xs)
    if not xs: return None
    return xs[n//2] if n%2 else (xs[n//2-1]+xs[n//2])/2

def detect_vwap_reclaim(bars, i, pc):
    if i < 1: return None
    a,b=bars[i-1],bars[i]
    ap=f(a,"average"); bp=f(b,"average")
    ac=f(a,"close"); bc=f(b,"close")
    if None in (ap,bp,ac,bc): return None
    prev_near_or_below = ac <= ap*1.002
    reclaim = bc > bp and bc > ac
    if not (prev_near_or_below and reclaim): return None
    stop=min(f(a,"low"), bp) if f(a,"low") is not None else bp
    return {"setup":"VWAP_RECLAIM","entry":bc,"stop":stop}

def detect_platform_breakout(bars, i, pc):
    if i < 4: return None
    prior=bars[i-4:i]; cur=bars[i]
    highs=[f(x,"high") for x in prior]; lows=[f(x,"low") for x in prior]
    vols=[f(x,"volume") or 0 for x in prior]
    if any(v is None for v in highs+lows): return None
    ph=max(highs); pl=min(lows)
    mid=(ph+pl)/2
    width=(ph-pl)/mid*100 if mid else 999
    cc=f(cur,"close"); cv=f(cur,"volume") or 0
    if width > 1.5 or cc is None: return None
    if not (cc > ph and cv > med(vols)*1.5): return None
    return {"setup":"PLATFORM_BREAKOUT","entry":cc,"stop":pl}

def detect_p3_rebreak(bars, i, pc):
    if i < 7: return None
    win=bars[i-7:i]
    cur=bars[i]
    closes=[f(x,"close") for x in win]
    highs=[f(x,"high") for x in win]
    lows=[f(x,"low") for x in win]
    avgs=[f(x,"average") for x in win]
    if any(v is None for v in closes+highs+lows): return None

    # Require an earlier impulse high, then a controlled pullback.
    peak_idx=max(range(len(highs)), key=lambda j: highs[j])
    if peak_idx > 4: return None
    peak=highs[peak_idx]
    pb_lows=lows[peak_idx+1:]
    if len(pb_lows)<2: return None
    pb_low=min(pb_lows)
    drawdown=(pb_low/peak-1)*100
    if not (-2.5 <= drawdown <= -0.5): return None

    # Pullback should not meaningfully lose cumulative average when available.
    valid_avg=[x for x in avgs[peak_idx+1:] if x is not None]
    if valid_avg and pb_low < min(valid_avg)*0.995: return None

    recent_high=max(highs[-2:])
    cc=f(cur,"close")
    if cc is None or cc <= recent_high: return None

    return {"setup":"P3_REBREAK","entry":cc,"stop":pb_low}

DETECTORS=[detect_vwap_reclaim, detect_platform_breakout, detect_p3_rebreak]

def validate_trade(sig):
    if sig is None:
        return None
    entry,stop=sig["entry"],sig["stop"]
    if entry is None or stop is None or stop >= entry: return None
    risk_pct=(entry-stop)/entry*100
    if not (MIN_RISK_PCT <= risk_pct <= MAX_RISK_PCT):
        return None
    sig={**sig,"risk_pct":risk_pct}
    return sig

def simulate(bars, i, sig, target_r):
    entry=sig["entry"]; stop=sig["stop"]
    risk=entry-stop
    target=entry+risk*target_r
    end=min(len(bars)-1,i+MAX_HOLD_BARS)
    exit_px=f(bars[end],"close"); exit_reason="TIME"
    exit_i=end
    mfe=-999; mae=999
    for j in range(i+1,end+1):
        hi=f(bars[j],"high"); lo=f(bars[j],"low")
        if hi is None or lo is None: continue
        mfe=max(mfe,(hi-entry)/risk)
        mae=min(mae,(lo-entry)/risk)
        stop_hit=lo<=stop
        target_hit=hi>=target
        if stop_hit and target_hit:
            exit_px=stop; exit_reason="STOP_AMBIGUOUS"; exit_i=j; break
        if stop_hit:
            exit_px=stop; exit_reason="STOP"; exit_i=j; break
        if target_hit:
            exit_px=target; exit_reason=f"TP_{target_r}R"; exit_i=j; break

    gross_r=(exit_px-entry)/risk
    cost_r=COST_PCT/sig["risk_pct"]
    net_r=gross_r-cost_r
    return {
        "target_r":target_r,
        "exit_reason":exit_reason,
        "bars_held":exit_i-i,
        "gross_r":gross_r,
        "net_r":net_r,
        "mfe_r":None if mfe==-999 else mfe,
        "mae_r":None if mae==999 else mae,
        "entry":entry,"stop":stop,"target":target,
    }

def scan_file(path):
    obj=json.loads(path.read_text(encoding="utf-8"))
    by=group_day(obj["data"]); pc=prev_close_map(by)
    trades=[]
    for d,bars in by.items():
        if pc[d] in (None,0): continue
        used=set()
        for i in range(1,len(bars)):
            # one trade per setup/day to avoid repeated overlapping signals.
            for det in DETECTORS:
                sig=validate_trade(det(bars,i,pc[d]))
                if not sig or sig["setup"] in used:
                    continue
                entry=sig["entry"]
                if entry > 100: continue
                change_pct=(entry/pc[d]-1)*100
                if change_pct <= 0: continue

                for target_r in (1.5,2.0):
                    sim=simulate(bars,i,sig,target_r)
                    trades.append({
                        "symbol":obj["symbol"],
                        "exchange":obj.get("exchange"),
                        "date":str(d),
                        "trigger_time":bars[i]["_dt"].strftime("%H:%M"),
                        "change_pct":change_pct,
                        "setup":sig["setup"],
                        "risk_pct":sig["risk_pct"],
                        **sim,
                    })
                used.add(sig["setup"])
    return trades

def metrics(rows):
    if not rows: return {"n":0}
    vals=[r["net_r"] for r in rows]
    wins=[x for x in vals if x>0]; losses=[x for x in vals if x<0]
    gp=sum(wins); gl=-sum(losses)
    return {
        "n":len(vals),
        "win_rate":sum(x>0 for x in vals)/len(vals),
        "expectancy_r":statistics.mean(vals),
        "median_r":statistics.median(vals),
        "pf":gp/gl if gl>0 else None,
        "avg_win_r":statistics.mean(wins) if wins else None,
        "avg_loss_r":statistics.mean(losses) if losses else None,
        "avg_mfe_r":statistics.mean([r["mfe_r"] for r in rows if r["mfe_r"] is not None]),
        "avg_mae_r":statistics.mean([r["mae_r"] for r in rows if r["mae_r"] is not None]),
    }

def by_year(rows):
    ys=sorted({r["date"][:4] for r in rows})
    return {y:metrics([r for r in rows if r["date"].startswith(y)]) for y in ys}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",default="research_data/history")
    ap.add_argument("--out",default="research_output_trigger")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    trades=[]
    for p in sorted(Path(args.data_dir).glob("*_5.json")):
        trades.extend(scan_file(p))

    report={
        "scope":"Event-based trigger backtest on deterministic 100-symbol sample.",
        "cost_pct":COST_PCT,
        "risk_bounds_pct":[MIN_RISK_PCT,MAX_RISK_PCT],
        "max_hold_minutes":MAX_HOLD_BARS*5,
        "intrabar_ambiguity_rule":"If stop and target are both touched in one 5m bar, stop is assumed first.",
        "results":{},
        "limitations":[
            "Current listing universe sampled backward; survivorship bias remains.",
            "5m OHLC cannot reveal intrabar path; ambiguity handled conservatively.",
            "No order-book/slippage model beyond fixed cost assumption.",
            "This is research, not authorization for A+ or live deployment."
        ],
    }

    for setup in ["VWAP_RECLAIM","PLATFORM_BREAKOUT","P3_REBREAK"]:
        report["results"][setup]={}
        for tr in (1.5,2.0):
            rs=[r for r in trades if r["setup"]==setup and r["target_r"]==tr]
            report["results"][setup][f"{tr}R"]={"all":metrics(rs),"by_year":by_year(rs)}

    candidates=[]
    for setup,targets in report["results"].items():
        for target_name,obj in targets.items():
            m=obj["all"]; byy=obj["by_year"]
            tested=[x for x in byy.values() if x.get("n",0)>=30]
            positive=sum(1 for x in tested if (x.get("expectancy_r") or 0)>0 and (x.get("pf") or 0)>1)
            if m.get("n",0)>=200 and (m.get("expectancy_r") or -99)>0 and (m.get("pf") or 0)>1 and len(tested)>=2 and positive>=max(2,len(tested)-1):
                candidates.append({"setup":setup,"target":target_name,"metrics":m,
                                   "tested_years":len(tested),"positive_years":positive})

    if candidates:
        verdict="PASS_TO_OOS_VALIDATION"
    else:
        verdict="REVISE_OR_REJECT_TRIGGERS"

    report["verdict"]=verdict
    report["promotion_candidates"]=candidates

    (out/"trigger_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    if trades:
        fields=sorted({k for r in trades for k in r})
        with (out/"trigger_trades.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(trades)

    lines=["# Sky Trigger Event Backtest",f"- Verdict: **{verdict}**",f"- Cost assumption: {COST_PCT}%",
           f"- Total trade-path rows: {len(trades)}",""]
    for setup,targets in report["results"].items():
        lines.append(f"## {setup}")
        for target,obj in targets.items():
            m=obj["all"]
            lines.append(f"- {target}: n={m.get('n')} expR={m.get('expectancy_r')} PF={m.get('pf')} win={m.get('win_rate')}")
    lines += ["","## Limits","- Research only; A+ remains prohibited.","- Survivorship bias remains.",
              "- 5m intrabar ambiguity treated conservatively."]
    (out/"trigger_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
