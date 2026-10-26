from __future__ import annotations

import argparse, csv, json, sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from research.backtest_opening_acceleration_baseline_c import (
    PRIMARY_COST, STRESS_COST, build_snapshot_db, enrich_rows, select_variant,
    metrics, concentration, subgroup,
)


def minute_plus(hhmm: str, minutes: int = 1) -> str:
    return (datetime.strptime(hhmm, "%H:%M") + timedelta(minutes=minutes)).strftime("%H:%M")


def load_day_map(root: str) -> dict:
    out={}
    for p in sorted(Path(root).rglob("*_opening_1m.json")):
        x=json.loads(p.read_text(encoding="utf-8"))
        symbol=str(x.get("symbol") or "")
        for d in x.get("days") or []:
            day=str(d.get("date") or "")
            if day:
                out[(day,symbol)]={**d,"exchange":x.get("exchange")}
    return out


def write_csv(path, rows):
    if not rows:
        Path(path).write_text("",encoding="utf-8"); return
    keys=sorted({k for r in rows for k in r})
    with Path(path).open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=keys); w.writeheader(); w.writerows(rows)


def apply_outcome(seed, day_obj, entry_obs, branch):
    o=dict((day_obj.get("outcomes") or {}).get(entry_obs) or {})
    if o.get("entry_status")!="ENTRY_4TICK_ZONE" or not o.get("entry"):
        return None
    d=dict(seed)
    d["branch"]=branch
    d["baseline_c_seed_obs"]=seed["obs"]
    d["e_entry_obs"]=entry_obs
    d["entry"]=float(o["entry"])
    for k,v in o.items():
        if k not in {"entry"}:
            d[k]=v
    exit60=d.get("stop_aware_exit_60m") or d.get("exit_60m")
    exit30=d.get("stop_aware_exit_30m") or d.get("exit_30m")
    d["gross_30m"]=(float(exit30)/d["entry"]-1) if exit30 else None
    d["gross_60m"]=(float(exit60)/d["entry"]-1) if exit60 else None
    d["gross_close"]=(float(d["session_close"])/d["entry"]-1) if d.get("session_close") else None
    d["net_60m_045"]=d["gross_60m"]-PRIMARY_COST if d["gross_60m"] is not None else None
    d["net_60m_065"]=d["gross_60m"]-STRESS_COST if d["gross_60m"] is not None else None
    d["mfe_60m"]=(float(d["high_60m"])/d["entry"]-1) if d.get("high_60m") else None
    d["mae_60m"]=(float(d["low_60m"])/d["entry"]-1) if d.get("low_60m") else None
    d["mfe_to_close"]=(float(d["high_to_close"])/d["entry"]-1) if d.get("high_to_close") else None
    d["mae_to_close"]=(float(d["low_to_close"])/d["entry"]-1) if d.get("low_to_close") else None
    d["hit_plus5"]=bool(d["mfe_to_close"] is not None and d["mfe_to_close"]>=0.05)
    d["open_stop_hit"]=bool(d.get("open_stop_triggered"))
    d["near_limit_proxy"]=bool(
        d.get("high_to_close") is not None and d.get("prior_close")
        and float(d["high_to_close"])/float(d["prior_close"])-1>=0.095
    )
    return d


def classify(seed, day_obj):
    bars=dict(day_obj.get("bars") or {})
    op=float(day_obj["session_open"])
    labels=sorted(k for k in bars if seed["obs"] <= k <= "09:14")
    pulled=False
    for label in labels:
        b=bars.get(label) or {}
        lo=b.get("low")
        prev=bars.get(minute_plus(label,-1)) or {}
        close=b.get("close")
        prev_high=prev.get("high")

        if not pulled and lo is not None and float(lo)<=op:
            pulled=True
            continue

        if close is None or prev_high is None:
            continue

        confirm = float(close)>op and float(close)>float(prev_high)
        if not confirm:
            continue

        entry_obs=minute_plus(label,1)
        if entry_obs>"09:15":
            return ("NO_CONFIRMATION_BY_ENTRY_WINDOW",{"confirm_obs":label,"entry_obs":entry_obs})

        o=dict((day_obj.get("outcomes") or {}).get(entry_obs) or {})
        branch="PATH_B" if pulled else "PATH_A"
        if o.get("entry_status")=="ENTRY_4TICK_ZONE" and o.get("entry"):
            return (f"{branch}_ENTRY",{"confirm_obs":label,"entry_obs":entry_obs})
        return (f"{branch}_MISSED_4TICK",{"confirm_obs":label,"entry_obs":entry_obs})

    if pulled:
        return ("PULLBACK_NO_RECLAIM",{})
    return ("NO_CONFIRMATION_BY_ENTRY_WINDOW",{})


def adjudicate(primary, half, conc):
    if primary.get("n",0)<200: return "HOLD_INSUFFICIENT_SAMPLE"
    if primary.get("expectancy") is None or primary["expectancy"]<=0:
        return "REJECT_AFTER_COST_EXPECTANCY"
    if primary.get("pf") is None or primary["pf"]<=1:
        return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0)>0.20:
        return "HOLD_CONCENTRATION_FAIL"
    h1=half.get("2026-H1",{}); h2=half.get("2026-H2",{})
    if min(h1.get("n",0),h2.get("n",0))<50:
        return "HOLD_HALF_SAMPLE"
    if (h1.get("expectancy") is None or h2.get("expectancy") is None
        or (h1["expectancy"]>0)!=(h2["expectancy"]>0)):
        return "HOLD_HALF_INSTABILITY"
    return "PROMOTE_CANDIDATE_TO_W4"


def run(data_root, out_dir, source_run_id):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    db=out/"baseline_e_seed.sqlite"
    if db.exists(): db.unlink()
    build=build_snapshot_db(data_root,str(db))
    conn=sqlite3.connect(db)
    rows=enrich_rows(conn); conn.close()
    seeds=select_variant(rows)
    day_map=load_day_map(data_root)

    disposition=[]; trades=[]
    for seed in seeds:
        day_obj=day_map.get((seed["session_date"],seed["symbol"]))
        if not day_obj: continue
        cls,meta=classify(seed,day_obj)
        disposition.append({
            "session_date":seed["session_date"],"symbol":seed["symbol"],
            "seed_obs":seed["obs"],"disposition":cls,**meta,
            "c_open_stop_hit":bool(seed.get("open_stop_hit")),
            "c_hit_plus5":bool(seed.get("hit_plus5")),
        })
        if cls not in {"PATH_A_ENTRY","PATH_B_ENTRY"}:
            continue
        branch=cls.replace("_ENTRY","")
        d=apply_outcome(seed,day_obj,meta["entry_obs"],branch)
        if d is not None:
            d["confirm_obs"]=meta["confirm_obs"]
            trades.append(d)

    write_csv(out/"baseline_e_disposition.csv",disposition)
    write_csv(out/"opening_acceleration_baseline_e_trades.csv",trades)

    branches={}
    for branch in ("PATH_A","PATH_B"):
        arr=[x for x in trades if x["branch"]==branch]
        branches[branch]={
            "selected":len(arr),
            "gross_60m":metrics(arr,"gross_60m"),
            "cost_045":metrics(arr,"net_60m_045"),
            "cost_065":metrics(arr,"net_60m_065"),
            "half_045":subgroup(arr,"half","net_60m_045"),
            "concentration":concentration(arr),
        }

    disp=defaultdict(list)
    for r in disposition: disp[r["disposition"]].append(r)
    disp_summary={}
    for k,arr in sorted(disp.items()):
        disp_summary[k]={
            "n":len(arr),
            "share":len(arr)/len(disposition) if disposition else 0,
            "c_open_stop_rate":sum(bool(x["c_open_stop_hit"]) for x in arr)/len(arr),
            "c_plus5_rate":sum(bool(x["c_hit_plus5"]) for x in arr)/len(arr),
        }

    p045=metrics(trades,"net_60m_045")
    p065=metrics(trades,"net_60m_065")
    gross=metrics(trades,"gross_60m")
    half=subgroup(trades,"half","net_60m_045")
    conc=concentration(trades)
    decision=adjudicate(p045,half,conc)

    report={
        "schema_version":"OPENING_ACCELERATION_BASELINE_E_DUAL_PATH_V1_0",
        "preregistered_spec":"research/w5/OPENING_ACCELERATION_BASELINE_E_DUAL_PATH_PREREGISTRATION_20261027.md",
        "source":{"baseline_c_source_run_id":source_run_id,"historical_window":"2026-01-01/2026-10-22","fresh_oos":False},
        "build":build,
        "seed_population":len(seeds),
        "disposition":disp_summary,
        "branches":branches,
        "combined":{
            "selected":len(trades),
            "gross_60m":gross,
            "cost_045":p045,
            "cost_065":p065,
            "half_045":half,
            "entry_minute_045":subgroup(trades,"e_entry_obs","net_60m_045"),
            "concentration":conc,
        },
        "decision":decision,
        "governance":{"production_change":False,"fresh_oos_claim":False,"next_if_survives":"W4_SHADOW_PAPER_ONLY"},
    }
    (out/"opening_acceleration_baseline_e_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"opening_acceleration_baseline_e_report.md").write_text(
        "# Opening Acceleration Baseline E — Dual Path\n\n"
        f"- Decision: **{decision}**\n"
        f"- Seeds: {len(seeds):,}\n"
        f"- Combined selected: {len(trades):,}\n"
        f"- Gross expectancy: {gross.get('expectancy')}\n"
        f"- 0.45% expectancy: {p045.get('expectancy')}\n"
        f"- 0.45% PF: {p045.get('pf')}\n"
        f"- 0.65% expectancy: {p065.get('expectancy')}\n"
        f"- 0.65% PF: {p065.get('pf')}\n\n"
        "## Branches\n\n"+json.dumps(branches,ensure_ascii=False,indent=2)+"\n\n"
        "## Disposition\n\n"+json.dumps(disp_summary,ensure_ascii=False,indent=2)+"\n"
        "\n2026 is structural research data, not fresh OOS. No Production change.\n",
        encoding="utf-8"
    )
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--source-run-id",default="40267006806")
    args=ap.parse_args()
    print(json.dumps(run(args.data_root,args.out_dir,args.source_run_id),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
