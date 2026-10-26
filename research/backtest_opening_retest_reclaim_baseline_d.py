from __future__ import annotations

import argparse, csv, json
from collections import defaultdict
from pathlib import Path

PRIMARY_COST=0.0045
STRESS_COST=0.0065
SCHEMA_VERSION="OPENING_RETEST_RECLAIM_BASELINE_D_V1_0"
SOURCE_SCHEMA="OPENING_ACCELERATION_1M_COMPACT_V1_1_4TICK_STOP"

def n(v):
    try: return float(v)
    except Exception: return None

def tick_size(price: float) -> float:
    if price < 10: return 0.01
    if price < 50: return 0.05
    if price < 100: return 0.10
    if price < 500: return 0.50
    if price < 1000: return 1.00
    return 5.00

def next_tick(price: float) -> float:
    return round(float(price)+tick_size(float(price)+1e-12),2)

def fourth_tick_above(price: float) -> float:
    x=float(price)
    for _ in range(4): x=next_tick(x)
    return x

def half_label(day: str) -> str:
    y,m,_=day.split("-")
    return f"{y}-H{1 if int(m)<=6 else 2}"

def detect_reclaim_entry(day: dict):
    so=n(day.get("session_open"))
    bars=day.get("bars") or {}
    outcomes=day.get("outcomes") or {}
    if so is None or so<=0: return None
    launch_level=fourth_tick_above(so)
    times=sorted(k for k in bars if "09:00" <= k <= "09:14")
    launch=None; retest=None; reclaim=None
    for hm in times:
        b=bars[hm]
        hi=n(b.get("high")); lo=n(b.get("low")); cl=n(b.get("close"))
        if hi is None or lo is None or cl is None: continue
        if launch is None:
            if cl>so and hi>=launch_level:
                launch=hm
            continue
        if retest is None:
            if hm>launch and lo<=so:
                retest=hm
            continue
        if reclaim is None and hm>retest and cl>so:
            reclaim=hm
            break
    if reclaim is None: return None
    h,m=map(int,reclaim.split(":"))
    entry_min=h*60+m+1
    eh,em=divmod(entry_min,60)
    entry_hm=f"{eh:02d}:{em:02d}"
    if entry_hm>"09:15": return None
    o=outcomes.get(entry_hm) or {}
    return {
      "session_open":so,"launch_time":launch,"retest_time":retest,
      "reclaim_time":reclaim,"entry_time":entry_hm,
      "entry_status":o.get("entry_status"),"entry":n(o.get("entry")),
      "raw_entry_open":n(o.get("raw_entry_open")),
      "max_entry_4tick":n(o.get("max_entry_4tick")),
      "exit_30m":n(o.get("stop_aware_exit_30m") or o.get("exit_30m")),
      "exit_60m":n(o.get("stop_aware_exit_60m") or o.get("exit_60m")),
      "session_close":n(o.get("session_close")),
      "high_60m":n(o.get("high_60m")),"low_60m":n(o.get("low_60m")),
      "high_to_close":n(o.get("high_to_close")),"low_to_close":n(o.get("low_to_close")),
      "open_stop_triggered":bool(o.get("open_stop_triggered")),
    }

def add_returns(t):
    e=t.get("entry")
    if not e: return t
    for label,key in [("gross_30m","exit_30m"),("gross_60m","exit_60m"),("gross_close","session_close")]:
        x=t.get(key); t[label]=x/e-1 if x else None
    t["net_60m_045"]=t["gross_60m"]-PRIMARY_COST if t.get("gross_60m") is not None else None
    t["net_60m_065"]=t["gross_60m"]-STRESS_COST if t.get("gross_60m") is not None else None
    t["mfe_60m"]=t["high_60m"]/e-1 if t.get("high_60m") else None
    t["mae_60m"]=t["low_60m"]/e-1 if t.get("low_60m") else None
    t["mfe_to_close"]=t["high_to_close"]/e-1 if t.get("high_to_close") else None
    t["hit_plus5"]=bool(t.get("mfe_to_close") is not None and t["mfe_to_close"]>=0.05)
    return t

def max_drawdown(trades,field):
    by_day=defaultdict(list)
    for t in trades:
        if t.get(field) is not None: by_day[t["session_date"]].append(float(t[field]))
    eq=peak=1.0;mdd=0.0
    for day in sorted(by_day):
        r=sum(by_day[day])/len(by_day[day]);eq*=1+r;peak=max(peak,eq);mdd=min(mdd,eq/peak-1)
    return mdd if by_day else None

def metrics(trades,field):
    vals=[float(t[field]) for t in trades if t.get(field) is not None]
    if not vals:return {"n":0}
    wins=[x for x in vals if x>0];loss=[x for x in vals if x<0]
    return {
      "n":len(vals),"expectancy":sum(vals)/len(vals),
      "pf":sum(wins)/abs(sum(loss)) if loss else None,
      "win_rate":len(wins)/len(vals),
      "avg_win":sum(wins)/len(wins) if wins else None,
      "avg_loss":sum(loss)/len(loss) if loss else None,
      "max_drawdown":max_drawdown(trades,field),
      "avg_mfe_60m":sum(t["mfe_60m"] for t in trades if t.get("mfe_60m") is not None)/max(1,sum(t.get("mfe_60m") is not None for t in trades)),
      "avg_mae_60m":sum(t["mae_60m"] for t in trades if t.get("mae_60m") is not None)/max(1,sum(t.get("mae_60m") is not None for t in trades)),
      "hit_plus5_rate":sum(bool(t.get("hit_plus5")) for t in trades)/len(trades),
      "open_stop_rate":sum(bool(t.get("open_stop_triggered")) for t in trades)/len(trades),
    }

def subgroup(trades,key,field):
    g=defaultdict(list)
    for t in trades:g[str(t.get(key))].append(t)
    return {k:metrics(v,field) for k,v in sorted(g.items())}

def concentration(trades):
    c=defaultdict(int)
    for t in trades:c[t["symbol"]]+=1
    total=len(trades)
    return {"unique_symbols":len(c),"max_symbol_share":max(c.values())/total if total else None,
            "top_symbols":sorted(({"symbol":k,"n":v,"share":v/total} for k,v in c.items()),key=lambda x:(-x["n"],x["symbol"]))[:20] if total else []}

def adjudicate(p,half,conc):
    if p.get("n",0)<200:return "HOLD_INSUFFICIENT_SAMPLE"
    if p.get("expectancy") is None or p["expectancy"]<=0:return "REJECT_AFTER_COST_EXPECTANCY"
    if p.get("pf") is None or p["pf"]<=1:return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0)>0.20:return "HOLD_CONCENTRATION_FAIL"
    for h in ("2026-H1","2026-H2"):
        m=half.get(h,{})
        if m.get("n",0)>=50 and (m.get("expectancy") is None or m["expectancy"]<=0 or (m.get("pf") or 0)<=1):
            return "HOLD_HALF_INSTABILITY"
    return "PROMOTE_CANDIDATE_TO_W4"

def run(data_root,out_dir,source_run_id=None):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    trades=[]; files=0; parse_errors=[]
    for p in sorted(Path(data_root).rglob("*_opening_1m.json")):
        files+=1
        try:
            x=json.loads(p.read_text(encoding="utf-8"))
            if x.get("schema_version")!=SOURCE_SCHEMA: raise ValueError("ineligible source schema")
            symbol=str(x.get("symbol") or "");exchange=str(x.get("exchange") or "")
            for d in x.get("days") or []:
                day=str(d.get("date") or "")
                z=detect_reclaim_entry(d)
                if not z or z.get("entry_status")!="ENTRY_4TICK_ZONE" or not z.get("entry"):continue
                z.update({"symbol":symbol,"exchange":exchange,"session_date":day,"half":half_label(day)})
                trades.append(add_returns(z))
        except Exception as exc:
            parse_errors.append({"file":str(p),"error":f"{type(exc).__name__}: {exc}"})
    p045=metrics(trades,"net_60m_045");p065=metrics(trades,"net_60m_065")
    half=subgroup(trades,"half","net_60m_045"); minute=subgroup(trades,"entry_time","net_60m_045")
    exchange=subgroup(trades,"exchange","net_60m_045");conc=concentration(trades)
    decision=adjudicate(p045,half,conc)
    report={
      "schema_version":SCHEMA_VERSION,
      "preregistered_spec":"research/w5/OPENING_RETEST_RECLAIM_BASELINE_D_PREREGISTRATION_20261026.md",
      "source":{"opening_1m_workflow_run_id":source_run_id},
      "build":{"files":files,"trades":len(trades),"parse_errors":parse_errors[:100]},
      "baseline":{
        "selected":len(trades),
        "gross_30m":metrics(trades,"gross_30m"),
        "gross_60m":metrics(trades,"gross_60m"),
        "gross_close":metrics(trades,"gross_close"),
        "cost_045":p045,"cost_065":p065,
        "half_045":half,"minute_045":minute,"exchange_045":exchange,
        "concentration":conc,
      },
      "decision":decision,
      "governance":{"production_change":False,"next_if_survives":"W4_SHADOW_PAPER_ONLY"}
    }
    with (out/"opening_retest_reclaim_baseline_d_trades.csv").open("w",newline="",encoding="utf-8") as fh:
        keys=sorted({k for r in trades for k in r}) if trades else []
        if keys:
            w=csv.DictWriter(fh,fieldnames=keys);w.writeheader();w.writerows(trades)
    (out/"opening_retest_reclaim_baseline_d_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    md=["# Opening Retest Reclaim — Baseline D Result","",f"- Decision: **{decision}**",f"- Selected: {len(trades):,}",
        f"- 0.45% expectancy: {p045.get('expectancy')}",f"- 0.45% PF: {p045.get('pf')}",
        f"- 0.65% expectancy: {p065.get('expectancy')}",f"- 0.65% PF: {p065.get('pf')}","","No Production change."]
    (out/"opening_retest_reclaim_baseline_d_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data-root",required=True);ap.add_argument("--out-dir",required=True);ap.add_argument("--source-run-id",default=None)
    a=ap.parse_args();print(json.dumps(run(a.data_root,a.out_dir,a.source_run_id),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
