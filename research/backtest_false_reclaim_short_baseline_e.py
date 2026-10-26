from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path

PRIMARY_COST=0.0045
STRESS_COST=0.0065
SCHEMA_VERSION="FALSE_RECLAIM_SHORT_BASELINE_E_V1_0"

def n(v):
    try:return float(v)
    except Exception:return None

def half_label(day):
    y,m,_=day.split("-");return f"{y}-H{1 if int(m)<=6 else 2}"

def max_drawdown(ts,field):
    by=defaultdict(list)
    for t in ts:
        if t.get(field) is not None:by[t["session_date"]].append(float(t[field]))
    if not by:return None
    eq=peak=1.0;mdd=0.0
    for d in sorted(by):
        r=sum(by[d])/len(by[d]);eq*=1+r;peak=max(peak,eq);mdd=min(mdd,eq/peak-1)
    return mdd

def metrics(ts,field):
    vals=[float(t[field]) for t in ts if t.get(field) is not None]
    if not vals:return {"n":0}
    w=[x for x in vals if x>0];l=[x for x in vals if x<0]
    return {"n":len(vals),"expectancy":sum(vals)/len(vals),"pf":sum(w)/abs(sum(l)) if l else None,"win_rate":len(w)/len(vals),
            "avg_win":sum(w)/len(w) if w else None,"avg_loss":sum(l)/len(l) if l else None,"max_drawdown":max_drawdown(ts,field),
            "open_stop_rate":sum(bool(t.get("open_stop_hit")) for t in ts)/len(ts),
            "hit_down5_rate":sum(bool(t.get("hit_down5")) for t in ts)/len(ts),
            "near_limit_down_rate":sum(bool(t.get("near_limit_down")) for t in ts)/len(ts)}

def subgroup(ts,key,field):
    g=defaultdict(list)
    for t in ts:g[str(t.get(key))].append(t)
    return {k:metrics(v,field) for k,v in sorted(g.items())}

def concentration(ts):
    c=defaultdict(int)
    for t in ts:c[t["symbol"]]+=1
    total=len(ts)
    return {"unique_symbols":len(c),"max_symbol_share":max(c.values())/total if total else None}

def load_trades(root):
    trades=[];files=sorted(Path(root).rglob("*_false_reclaim_short_1m.json"));errors=[]
    for p in files:
      try:
        x=json.loads(p.read_text(encoding="utf-8"))
        if x.get("schema_version")!="FALSE_RECLAIM_SHORT_1M_COMPACT_V1_0":continue
        symbol=str(x.get("symbol") or "");exchange=str(x.get("exchange") or "");prior_close=None
        for d in sorted(x.get("days") or [],key=lambda z:str(z.get("date") or "")):
            day=str(d.get("date") or "");op=n(d.get("session_open"));cl=n(d.get("session_close"));bars=d.get("bars") or {};outs=d.get("short_outcomes") or {}
            if not day or op is None or op<=0:
                if cl and cl>0:prior_close=cl
                continue
            strength=False;retest=False;reclaim=False
            for minute in [f"09:{m:02d}" for m in range(0,15)]:
                b=bars.get(minute)
                if not b:continue
                close=n(b.get("close"));low=n(b.get("low"))
                if not strength:
                    if close is not None and close>op:strength=True
                    continue
                if not retest:
                    if low is not None and low<=op:retest=True
                    continue
                if not reclaim:
                    if close is not None and close>op:reclaim=True
                    continue
                if close is None or close>=op:continue
                mm=int(minute.split(":")[1]);entry_min=mm+1
                if entry_min>15:break
                entry_obs=f"09:{entry_min:02d}";o=outs.get(entry_obs) or {}
                if o.get("entry_status")!="SHORT_ENTRY_4TICK_ZONE" or n(o.get("entry")) is None:break
                entry=n(o.get("entry"));exit30=n(o.get("stop_aware_exit_30m")) or n(o.get("exit_30m"));exit60=n(o.get("stop_aware_exit_60m")) or n(o.get("exit_60m"))
                gross30=entry/exit30-1 if entry and exit30 else None;gross60=entry/exit60-1 if entry and exit60 else None
                sess=n(o.get("session_close")) or cl;grossclose=entry/sess-1 if entry and sess else None
                lowclose=n(o.get("low_to_close"));highclose=n(o.get("high_to_close"))
                trades.append({"symbol":symbol,"exchange":exchange,"session_date":day,"breakdown_bar":minute,"entry_obs":entry_obs,"entry":entry,"session_open":op,"prior_close":prior_close,
                               "gross_30m":gross30,"gross_60m":gross60,"gross_close":grossclose,
                               "net_60m_045":gross60-PRIMARY_COST if gross60 is not None else None,"net_60m_065":gross60-STRESS_COST if gross60 is not None else None,
                               "open_stop_hit":bool(o.get("open_stop_triggered")),"hit_down5":bool(lowclose is not None and entry and entry/lowclose-1>=0.05),
                               "near_limit_down":bool(lowclose is not None and prior_close and lowclose/prior_close-1<=-0.095),
                               "mfe_to_close":entry/lowclose-1 if lowclose is not None and entry else None,"mae_to_close":entry/highclose-1 if highclose is not None and entry else None,
                               "half":half_label(day)})
                break
            if cl and cl>0:prior_close=cl
      except Exception as e:errors.append({"file":str(p),"error":f"{type(e).__name__}: {e}"})
    return trades,{"files":len(files),"parse_errors":errors[:50]}

def adjudicate(m,halves,conc):
    if m.get("n",0)<200:return "HOLD_INSUFFICIENT_SAMPLE"
    if m.get("expectancy") is None or m["expectancy"]<=0:return "REJECT_AFTER_COST_EXPECTANCY"
    if m.get("pf") is None or m["pf"]<=1:return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0)>0.20:return "HOLD_CONCENTRATION_FAIL"
    vals=[x for x in halves.values() if x.get("n",0)>=50]
    if len(vals)>=2 and any((x.get("expectancy") or 0)<=0 or (x.get("pf") or 0)<=1 for x in vals):return "HOLD_HALF_INSTABILITY"
    return "HOLD_SHORT_ELIGIBILITY_VALIDATION_REQUIRED"

def write_csv(path,rows):
    if not rows:path.write_text("",encoding="utf-8");return
    keys=sorted({k for r in rows for k in r})
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=keys);w.writeheader();w.writerows(rows)

def run(root,out_dir,source_run_id=None):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    ts,build=load_trades(root);write_csv(out/"false_reclaim_short_baseline_e_trades.csv",ts)
    gross=metrics(ts,"gross_60m");m045=metrics(ts,"net_60m_045");m065=metrics(ts,"net_60m_065");halves=subgroup(ts,"half","net_60m_045");mins=subgroup(ts,"entry_obs","net_60m_045");ex=subgroup(ts,"exchange","net_60m_045");conc=concentration(ts);decision=adjudicate(m045,halves,conc)
    rep={"schema_version":SCHEMA_VERSION,"source":{"pit_source_run_id":source_run_id},"selected":len(ts),"build":build,"gross_60m":gross,"cost_045":m045,"cost_065":m065,"half_045":halves,"minute_045":mins,"exchange_045":ex,"concentration":conc,"decision":decision,"execution_caveat":"Historical point-in-time short eligibility/borrowability is not yet gated.","governance":{"production_change":False,"next_if_survives":"EXECUTION_ELIGIBILITY_VALIDATION"}}
    (out/"false_reclaim_short_baseline_e_report.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"false_reclaim_short_baseline_e_report.md").write_text("# False-Reclaim Short — Baseline E\n\n"+f"- Decision: **{decision}**\n- Selected: {len(ts):,}\n- Gross 60m expectancy: {gross.get('expectancy')}\n- Gross PF: {gross.get('pf')}\n- 0.45% expectancy: {m045.get('expectancy')}\n- 0.45% PF: {m045.get('pf')}\n- 0.65% expectancy: {m065.get('expectancy')}\n- 0.65% PF: {m065.get('pf')}\n\nHistorical short eligibility/borrowability remains a required execution gate.\n",encoding="utf-8")
    return rep

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data-root",required=True);ap.add_argument("--out-dir",required=True);ap.add_argument("--source-run-id",default=None);a=ap.parse_args()
    print(json.dumps(run(a.data_root,a.out_dir,a.source_run_id),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
