from __future__ import annotations

import argparse, json, math, statistics
from collections import defaultdict
from pathlib import Path

COSTS=[0.45,0.65]
EXITS=["FIXED_3R","MA20_TRAIL","SWING10_TRAIL"]

def f(x):
    try:
        return float(x)
    except Exception:
        return None

def load_history(path):
    bysym={}
    for p in sorted(Path(path).glob("*_D.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o.get("symbol") or p.stem.replace("_D",""))
        rows=o.get("data") or o.get("rows") or o.get("history") or []
        arr=[]
        for r in rows:
            d=str(r.get("date") or r.get("trading_date") or "")[:10]
            op=f(r.get("open")); hi=f(r.get("high")); lo=f(r.get("low")); cl=f(r.get("close")); vol=f(r.get("volume"))
            if d and None not in (op,hi,lo,cl):
                arr.append({"date":d,"open":op,"high":hi,"low":lo,"close":cl,"volume":vol or 0.0})
        arr.sort(key=lambda x:x["date"])
        if arr:bysym[sym]=arr
    return bysym

def mean(xs): return statistics.mean(xs) if xs else None

def build_features(bysym):
    raw=[]
    for sym,days in bysym.items():
        closes=[x["close"] for x in days]
        highs=[x["high"] for x in days]
        for i in range(60,len(days)-21):
            ma20=mean(closes[i-19:i+1]); ma60=mean(closes[i-59:i+1])
            if not ma20 or not ma60 or closes[i-20] == 0: continue
            ret20=closes[i]/closes[i-20]-1
            prior20=max(highs[i-20:i])
            rng=(days[i]["high"]-days[i]["low"])/closes[i] if closes[i] else None
            raw.append({
                "symbol":sym,"idx":i,"date":days[i]["date"],"close":closes[i],
                "ma20":ma20,"ma60":ma60,"ret20":ret20,"prior20":prior20,
                "range_pct":rng,"days":days
            })
    bydate=defaultdict(list)
    for r in raw: bydate[r["date"]].append(r)
    out=[]
    for d,arr in bydate.items():
        eligible=[r for r in arr if r["close"]>0 and r["ma20"]>0]
        if len(eligible)<20: continue
        breadth=sum(r["close"]>r["ma20"] for r in eligible)/len(eligible)
        rs_sorted=sorted(r["ret20"] for r in eligible)
        for r in eligible:
            rank=sum(v<=r["ret20"] for v in rs_sorted)/len(rs_sorted)
            r["breadth"]=breadth; r["rs_pct"]=rank
            out.append(r)
    return out

def signal(r):
    if r["breadth"] < 0.50: return False
    if not (r["close"] > r["ma20"] > r["ma60"]): return False
    if r["rs_pct"] < 0.70: return False
    if not (r["close"] > r["prior20"]): return False
    if (r["close"]/r["ma20"]-1) > 0.08: return False
    if r["range_pct"] is None or r["range_pct"] > 0.08: return False
    days=r["days"]; i=r["idx"]; entry=days[i+1]["open"]
    if entry >= 100: return False
    stop=days[i]["low"]
    if stop >= entry: return False
    return True

def exit_trade(r, kind):
    days=r["days"]; i=r["idx"]; entry_i=i+1
    entry=days[entry_i]["open"]; init_stop=days[i]["low"]; risk=entry-init_stop
    target=entry+3*risk
    stop=init_stop
    max_i=min(entry_i+19,len(days)-1)
    exit_px=None; exit_i=None; reason=None
    for j in range(entry_i,max_i+1):
        day=days[j]
        if kind=="MA20_TRAIL" and j>entry_i and j>=20:
            prev_cl=[x["close"] for x in days[j-20:j]]
            trail=mean(prev_cl)
            if trail is not None: stop=max(init_stop,trail)
        elif kind=="SWING10_TRAIL" and j>entry_i and j>=10:
            swing10=min(x["low"] for x in days[j-10:j])
            stop=max(init_stop,swing10)
        if day["low"]<=stop:
            exit_px=day["open"] if day["open"]<stop else stop
            exit_i=j; reason="STOP"; break
        if kind=="FIXED_3R" and day["high"]>=target:
            exit_px=target; exit_i=j; reason="TARGET"; break
    if exit_px is None:
        exit_i=max_i; exit_px=days[exit_i]["close"]; reason="MAX_HOLD"
    gross_pct=(exit_px/entry-1)*100
    gross_r=(exit_px-entry)/risk if risk>0 else None
    return {
        "entry_date":days[entry_i]["date"],"exit_date":days[exit_i]["date"],
        "entry":entry,"stop":init_stop,"exit":exit_px,"reason":reason,
        "holding_days":exit_i-entry_i+1,"gross_pct":gross_pct,"gross_r":gross_r
    }

def metrics(vals, rvals):
    if not vals: return {"n":0}
    gp=sum(v for v in vals if v>0); gl=-sum(v for v in vals if v<0)
    cum=0.0; peak=0.0; mdd=0.0
    for rv in rvals:
        cum+=rv; peak=max(peak,cum); mdd=min(mdd,cum-peak)
    wins=[v for v in vals if v>0]; losses=[v for v in vals if v<0]
    return {
        "n":len(vals),"win_rate":sum(v>0 for v in vals)/len(vals),
        "expectancy_pct":statistics.mean(vals),
        "avg_win_pct":statistics.mean(wins) if wins else None,
        "avg_loss_pct":statistics.mean(losses) if losses else None,
        "pf":gp/gl if gl>0 else None,
        "expectancy_r":statistics.mean(rvals) if rvals else None,
        "max_drawdown_r":mdd
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_swing_v11")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    bysym=load_history(args.history_dir)
    feats=build_features(bysym)
    sig=[r for r in feats if signal(r)]
    report={
        "strategy":"Sky Swing Challenger V1.1",
        "spec":"research/SKY_SWING_CHALLENGER_V1_1_PREREGISTRATION.md",
        "symbols_loaded":len(bysym),"signals":len(sig),"results":{},
        "governance":"PREREGISTERED_CHALLENGER / NOT_PRODUCTION"
    }
    trades=[]
    for kind in EXITS:
        report["results"][kind]={}
        base=[]
        for r in sig:
            t=exit_trade(r,kind); t.update({"symbol":r["symbol"],"signal_date":r["date"],"exit_rule":kind,"rs_pct":r["rs_pct"],"breadth":r["breadth"]})
            base.append(t); trades.append(t)
        for c in COSTS:
            vals=[t["gross_pct"]-c for t in base]
            rvals=[]
            for t in base:
                risk=t["entry"]-t["stop"]
                cost_px=t["entry"]*(c/100)
                net_r=((t["exit"]-t["entry"])-cost_px)/risk if risk>0 else 0
                rvals.append(net_r)
            report["results"][kind][f"{c:.2f}"]=metrics(vals,rvals)

        yearly={}
        for y in sorted({t["signal_date"][:4] for t in base}):
            sub=[t for t in base if t["signal_date"].startswith(y)]
            vals=[t["gross_pct"]-0.45 for t in sub]
            rvals=[((t["exit"]-t["entry"])-t["entry"]*0.0045)/(t["entry"]-t["stop"]) for t in sub]
            yearly[y]=metrics(vals,rvals)
        report["results"][kind]["yearly_045"]=yearly

    Path(out/"swing_v11_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    Path(out/"swing_v11_trades.json").write_text(json.dumps(trades,ensure_ascii=False),encoding="utf-8")
    lines=["# Sky Swing Challenger V1.1 Canonical Replay",f"- symbols_loaded: {len(bysym)}",f"- signals: {len(sig)}"]
    for kind in EXITS:
        lines.append(f"\n## {kind}")
        for c in COSTS:
            m=report["results"][kind][f"{c:.2f}"]
            lines.append(f"- cost {c:.2f}%: n={m.get('n')} win={m.get('win_rate')} exp={m.get('expectancy_pct')} PF={m.get('pf')} ExpR={m.get('expectancy_r')} MDD_R={m.get('max_drawdown_r')}")
    Path(out/"swing_v11_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__": main()
