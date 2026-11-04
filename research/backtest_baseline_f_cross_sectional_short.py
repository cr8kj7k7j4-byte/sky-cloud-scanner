from __future__ import annotations
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from research.backtest_false_reclaim_short_baseline_e import load_trades as load_e, half_label

PRIMARY_COST=0.0045
STRESS_COST=0.0065

def numeric(v):
    try:
        x=float(v)
        return x if x==x and abs(x)!=float("inf") else None
    except (ValueError,TypeError):
        return None

def true_short(r):
    """Legacy E proxy = entry/cover-1; actual short return = (entry-cover)/entry."""
    if r is None or r<=-1:return None
    return r/(1+r)

def peer_census(data_root):
    """Completed minute closes vs session open for every PIT source symbol."""
    values=defaultdict(list)
    files=sorted(Path(data_root).rglob("*_false_reclaim_short_1m.json"))
    errors=[]
    for path in files:
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            if data.get("schema_version")!="FALSE_RECLAIM_SHORT_1M_COMPACT_V1_0":continue
            symbol=str(data.get("symbol") or "")
            exchange=str(data.get("exchange") or "")
            for day in data.get("days",[]):
                opening=numeric(day.get("session_open"))
                date=str(day.get("date") or "")
                if not opening or not date:continue
                for minute,bar in (day.get("bars") or {}).items():
                    cl=numeric(bar.get("close"))
                    if cl is None:continue
                    values[(exchange,date,minute)].append((symbol,cl/opening-1.0))
        except (ValueError,TypeError,OSError) as exc:
            errors.append({"file":str(path),"error":str(exc)})
    return values,{"input_files":len(files),"census_errors":errors[:20],"census_events":len(values)}

def contextualize(trades,census,min_peers=100):
    selected=[];all_repriced=[];excluded=defaultdict(int)
    for source in trades:
        t=dict(source)
        r=true_short(numeric(t.get("gross_60m")))
        if r is None:
            excluded["no_60m_outcome"]+=1
            continue
        t["gross_60m_corrected"]=r
        t["net_045"]=r-PRIMARY_COST
        t["net_065"]=r-STRESS_COST
        all_repriced.append(t)
        key=(t["exchange"],t["session_date"],t["breakdown_bar"])
        peers=[ret for sym,ret in census.get(key,()) if sym!=t["symbol"]]
        if len(peers)<min_peers:
            excluded["insufficient_contemporaneous_peers"]+=1
            continue
        market_median=statistics.median(peers)
        # Breakdown bar closes below open by design (E gate).
        barret=None
        # Contextual return is the completed breakdown-bar close vs session opening price.
        # Derive candidate return from same bar's peer-census value, not from future entry.
        for sym,ret in census.get(key,()):
            if sym==t["symbol"]:
                barret=ret
                break
        if barret is None:
            excluded["missing_candidate_completed_bar"]+=1
            continue
        t["peer_count"]=len(peers)
        t["exchange_market_median"]=market_median
        t["candidate_open_to_breakdown_close"]=barret
        t["cross_sectional_residual"]=barret-market_median
        if market_median>=0:
            excluded["market_not_broadly_weak"]+=1
            continue
        if barret>=market_median:
            excluded["candidate_not_relatively_weak"]+=1
            continue
        selected.append(t)
    return selected,all_repriced,dict(excluded)

def score(rows,key):
    values=[float(t[key]) for t in rows if t.get(key) is not None]
    if not values:return {"n":0,"expectancy":None,"pf":None,"win_rate":None}
    winners=[x for x in values if x>0]
    losers=[x for x in values if x<0]
    by_symbol=defaultdict(int)
    for t in rows:
        if t.get(key) is not None:by_symbol[t["symbol"]]+=1
    return {
      "n":len(values),
      "expectancy":sum(values)/len(values),
      "pf":sum(winners)/-sum(losers) if losers else None,
      "win_rate":len(winners)/len(values),
      "open_stop_rate":sum(bool(t.get("open_stop_hit")) for t in rows if t.get(key) is not None)/len(values),
      "max_single_symbol_share":max(by_symbol.values())/len(values) if by_symbol else None,
      "unique_symbols":len(by_symbol),
      "trading_days":len({t["session_date"] for t in rows if t.get(key) is not None}),
    }

def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8");return
    fields=sorted({k for row in rows for k in row})
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def run(data_root,out_dir,source_run_id):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    source,build=load_e(data_root)
    census,coverage=peer_census(data_root)
    selected,repriced,exclusions=contextualize(source,census)
    gross=score(selected,"gross_60m_corrected")
    net=score(selected,"net_045")
    stressed=score(selected,"net_065")
    control=score(repriced,"net_045")
    halves={k:score([t for t in selected if t["half"]==k],"net_045") for k in sorted({t["half"] for t in selected})}
    if net["n"]<200:decision="HOLD_INSUFFICIENT_SAMPLE"
    elif net["expectancy"]<=0:decision="REJECT_AFTER_COST_EXPECTANCY"
    elif net["pf"] is None or net["pf"]<=1:decision="REJECT_AFTER_COST_PF"
    else:decision="HOLD_REQUIRES_FRESH_OOS_SHORT_ELIGIBILITY"
    report={
      "schema":"BASELINE_F_CROSS_SECTIONAL_MARKET_CONFIRMED_SHORT_V1",
      "research_class":"EXPLORATORY_REUSED_HISTORICAL_DATA_NOT_FRESH_OOS",
      "preregistration":"research/w5/BASELINE_F_CROSS_SECTIONAL_FALSE_RECLAIM_PREREG_20261104.md",
      "source_run_id":source_run_id,
      "input":build,"market_census":coverage,
      "input_e_events":len(source),"e_60m_corrected_control":control,
      "selection_exclusions":exclusions,"f_selected":len(selected),
      "gross_60m":gross,"net_cost_045":net,"net_cost_065":stressed,
      "half_year_net_045":halves,"decision":decision,
      "short_eligibility_pit_verified":False,"borrowability_verified":False,
      "fresh_oos":False,"production_changed":False,
    }
    (out/"baseline_f_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    write_csv(out/"baseline_f_selected.csv",selected)
    lines=["# Baseline F | Cross-sectional False-Reclaim Short","","- Decision: **"+decision+"**",
       "- F 60m evaluable: "+str(net["n"]),
       "- F gross expectancy: "+str(gross["expectancy"]),
       "- F 0.45% expectancy / PF: "+str(net["expectancy"])+" / "+str(net["pf"]),
       "- F 0.65% expectancy / PF: "+str(stressed["expectancy"])+" / "+str(stressed["pf"]),
       "- Repriced all-E 0.45% expectancy / PF (corrected true short PnL): "+str(control["expectancy"])+" / "+str(control["pf"]),
       "- Fresh OOS: **NO**; historical short eligibility and borrowability: **NOT VERIFIED**.",
       "- No production change and no permission to trade."]
    (out/"baseline_f_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if build.get("parse_errors") or coverage.get("census_errors") or coverage.get("input_files",0)<1900:
        raise RuntimeError("INPUT_INTEGRITY_GATE_FAIL")
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("--data-root",required=True);p.add_argument("--out-dir",required=True);p.add_argument("--source-run-id",default="40329668748")
    a=p.parse_args();run(a.data_root,a.out_dir,a.source_run_id)
if __name__=="__main__":main()
