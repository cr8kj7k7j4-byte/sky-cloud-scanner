from __future__ import annotations

import argparse, csv, json
from collections import defaultdict
from pathlib import Path

PRIMARY_COST=0.0045
STRESS_COST=0.0065
SCHEMA_VERSION="OPENING_RETEST_RECLAIM_BASELINE_D_V1_0"

def n(v):
    try:return float(v)
    except Exception:return None

def max_drawdown(trades,field):
    by_day=defaultdict(list)
    for t in trades:
        if t.get(field) is not None: by_day[t["session_date"]].append(float(t[field]))
    if not by_day:return None
    eq=peak=1.0;mdd=0.0
    for d in sorted(by_day):
        r=sum(by_day[d])/len(by_day[d]);eq*=1+r;peak=max(peak,eq);mdd=min(mdd,eq/peak-1)
    return mdd

def metrics(trades,field):
    vals=[float(t[field]) for t in trades if t.get(field) is not None]
    if not vals:return {"n":0}
    wins=[x for x in vals if x>0];losses=[x for x in vals if x<0]
    return {
      "n":len(vals),"expectancy":sum(vals)/len(vals),
      "pf":sum(wins)/abs(sum(losses)) if losses else None,
      "win_rate":len(wins)/len(vals),
      "avg_win":sum(wins)/len(wins) if wins else None,
      "avg_loss":sum(losses)/len(losses) if losses else None,
      "max_drawdown":max_drawdown(trades,field),
      "open_stop_rate":sum(bool(t.get("open_stop_hit")) for t in trades)/len(trades),
      "hit_plus5_rate":sum(bool(t.get("hit_plus5")) for t in trades)/len(trades),
      "near_limit_proxy_rate":sum(bool(t.get("near_limit_proxy")) for t in trades)/len(trades),
    }

def half_label(day):
    y,m,_=day.split("-");return f"{y}-H{1 if int(m)<=6 else 2}"

def load_trades(data_root):
    trades=[];seen=set();files=sorted(Path(data_root).rglob("*_opening_1m.json"))
    parse_errors=[]
    for p in files:
        try:
            x=json.loads(p.read_text(encoding="utf-8"))
            if x.get("schema_version")!="OPENING_ACCELERATION_1M_COMPACT_V1_1_4TICK_STOP":
                continue
            symbol=str(x.get("symbol") or "");exchange=str(x.get("exchange") or "")
            prior_close=None
            for d in sorted(x.get("days") or [],key=lambda z:str(z.get("date") or "")):
                day=str(d.get("date") or "");op=n(d.get("session_open"));cl=n(d.get("session_close"))
                if not day or op is None or op<=0:
                    if cl and cl>0:prior_close=cl
                    continue
                bars=d.get("bars") or {};outs=d.get("outcomes") or {}
                strength=False;retest=False
                for minute in [f"09:{m:02d}" for m in range(0,15)]:
                    b=bars.get(minute)
                    if not b:continue
                    close=n(b.get("close"));low=n(b.get("low"))
                    if not strength:
                        if close is not None and close>op: strength=True
                        continue
                    if not retest:
                        if low is not None and low<=op: retest=True
                        continue
                    if close is None or close<=op: continue
                    mm=int(minute.split(":")[1]);entry_min=mm+1
                    if entry_min>15:break
                    entry_obs=f"09:{entry_min:02d}"
                    o=outs.get(entry_obs) or {}
                    if o.get("entry_status")!="ENTRY_4TICK_ZONE" or n(o.get("entry")) is None:
                        retest=False
                        continue
                    key=(day,symbol)
                    if key in seen:break
                    seen.add(key)
                    entry=n(o.get("entry"))
                    exit30=n(o.get("stop_aware_exit_30m")) or n(o.get("exit_30m"))
                    exit60=n(o.get("stop_aware_exit_60m")) or n(o.get("exit_60m"))
                    session_close=n(o.get("session_close")) or cl
                    gross30=exit30/entry-1 if entry and exit30 else None
                    gross60=exit60/entry-1 if entry and exit60 else None
                    grossclose=session_close/entry-1 if entry and session_close else None
                    highclose=n(o.get("high_to_close"));lowclose=n(o.get("low_to_close"))
                    trades.append({
                      "symbol":symbol,"exchange":exchange,"session_date":day,
                      "reclaim_bar":minute,"entry_obs":entry_obs,"entry":entry,
                      "session_open":op,"prior_close":prior_close,
                      "gross_30m":gross30,"gross_60m":gross60,"gross_close":grossclose,
                      "net_60m_045":gross60-PRIMARY_COST if gross60 is not None else None,
                      "net_60m_065":gross60-STRESS_COST if gross60 is not None else None,
                      "open_stop_hit":bool(o.get("open_stop_triggered")),
                      "hit_plus5":bool(highclose is not None and entry and highclose/entry-1>=0.05),
                      "near_limit_proxy":bool(highclose is not None and prior_close and highclose/prior_close-1>=0.095),
                      "mfe_to_close":highclose/entry-1 if highclose is not None and entry else None,
                      "mae_to_close":lowclose/entry-1 if lowclose is not None and entry else None,
                      "half":half_label(day)
                    })
                    break
                if cl and cl>0:prior_close=cl
        except Exception as e:
            parse_errors.append({"file":str(p),"error":f"{type(e).__name__}: {e}"})
    return trades,{"files":len(files),"parse_errors":parse_errors[:50]}

def concentration(trades):
    c=defaultdict(int)
    for t in trades:c[t["symbol"]]+=1
    total=len(trades)
    return {"unique_symbols":len(c),"max_symbol_share":max(c.values())/total if total else None}

def subgroup(trades,key,field):
    g=defaultdict(list)
    for t in trades:g[str(t.get(key))].append(t)
    return {k:metrics(v,field) for k,v in sorted(g.items())}

def write_csv(path,rows):
    if not rows:path.write_text("",encoding="utf-8");return
    keys=sorted({k for r in rows for k in r})
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=keys);w.writeheader();w.writerows(rows)

def adjudicate(m,halves,conc):
    if m.get("n",0)<200:return "HOLD_INSUFFICIENT_SAMPLE"
    if m.get("expectancy") is None or m["expectancy"]<=0:return "REJECT_AFTER_COST_EXPECTANCY"
    if m.get("pf") is None or m["pf"]<=1:return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0)>0.20:return "HOLD_CONCENTRATION_FAIL"
    vals=[x for x in halves.values() if x.get("n",0)>=50]
    if len(vals)>=2 and any((x.get("expectancy") or 0)<=0 or (x.get("pf") or 0)<=1 for x in vals):
        return "HOLD_HALF_INSTABILITY"
    return "PROMOTE_CANDIDATE_TO_W4"

def run(data_root,out_dir,source_run_id=None):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    trades,build=load_trades(data_root)
    write_csv(out/"opening_retest_reclaim_baseline_d_trades.csv",trades)
    m045=metrics(trades,"net_60m_045");m065=metrics(trades,"net_60m_065");gross=metrics(trades,"gross_60m")
    halves=subgroup(trades,"half","net_60m_045");minute=subgroup(trades,"entry_obs","net_60m_045");exch=subgroup(trades,"exchange","net_60m_045");conc=concentration(trades)
    decision=adjudicate(m045,halves,conc)
    rep={"schema_version":SCHEMA_VERSION,"preregistered_spec":"research/w5/OPENING_RETEST_RECLAIM_BASELINE_D_PREREGISTRATION_20261026.md","source":{"opening_1m_workflow_run_id":source_run_id},"build":build,"selected":len(trades),"gross_60m":gross,"cost_045":m045,"cost_065":m065,"half_045":halves,"minute_045":minute,"exchange_045":exch,"concentration":conc,"decision":decision,"governance":{"production_change":False,"baseline_c_retuned":False,"next_if_survives":"W4_SHADOW_PAPER_ONLY"}}
    (out/"opening_retest_reclaim_baseline_d_report.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"opening_retest_reclaim_baseline_d_report.md").write_text("# Opening Retest Reclaim — Baseline D Result\n\n"+f"- Decision: **{decision}**\n- Selected: {len(trades):,}\n"+f"- Gross 60m expectancy: {gross.get('expectancy')}\n- Gross PF: {gross.get('pf')}\n"+f"- 0.45% expectancy: {m045.get('expectancy')}\n- 0.45% PF: {m045.get('pf')}\n"+f"- 0.65% expectancy: {m065.get('expectancy')}\n- 0.65% PF: {m065.get('pf')}\n\n"+"## Half-year 0.45%\n\n"+json.dumps(halves,ensure_ascii=False,indent=2)+"\n\nNo Production change.\n",encoding="utf-8")
    return rep

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data-root",required=True);ap.add_argument("--out-dir",required=True);ap.add_argument("--source-run-id",default=None)
    a=ap.parse_args();print(json.dumps(run(a.data_root,a.out_dir,a.source_run_id),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
