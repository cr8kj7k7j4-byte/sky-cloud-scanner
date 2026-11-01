from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

AUDIT_DATES=["2023-12-31","2024-12-31","2025-12-31","2026-09-30"]
MIN_COVERAGE=95.0

def _contains(i,d):
    a=str(i.get("listed_from") or ""); b=i.get("listed_to")
    return bool(a and a<=d and (not b or d<=str(b)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--pit-json",required=True)
    ap.add_argument("--shard-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    pit=json.loads(Path(args.pit_json).read_text(encoding="utf-8"))
    intervals=pit.get("intervals") or []
    history={}
    duplicates=[]
    nonadjusted=[]
    observed=defaultdict(set)
    for p in sorted(Path(args.history_dir).glob("*_D.json")):
        obj=json.loads(p.read_text(encoding="utf-8"))
        sym=str(obj.get("symbol") or p.stem.split("_")[0])
        if not obj.get("adjusted"):
            nonadjusted.append(sym); continue
        dates=[]
        seen=set()
        for b in obj.get("data") or []:
            d=str(b.get("date") or "")
            k=(str(b.get("exchange") or ""),d)
            if k in seen: duplicates.append({"symbol":sym,"exchange":k[0],"date":d})
            seen.add(k)
            if d: dates.append(d); observed[sym].add(d)
        if dates:
            history[sym]={"min_date":min(dates),"max_date":max(dates),"bars":len(dates)}

    shard_reports=[]
    failed=[]; quarantined=[]; empty=[]
    for p in sorted(Path(args.shard_root).glob("shard_report_*.json")):
        x=json.loads(p.read_text(encoding="utf-8")); shard_reports.append(x)
        failed.extend(x.get("symbols_failed") or [])
        quarantined.extend(x.get("symbols_quarantined") or [])
        empty.extend(x.get("symbols_empty") or [])

    dates={}
    all_pass=bool(pit.get("historical_universe_gate_pass") and (pit.get("interval_validation") or {}).get("valid"))
    for d in AUDIT_DATES:
        eligible=sorted({str(i["symbol"]) for i in intervals if i.get("symbol") and _contains(i,d)})
        covered=sorted([s for s in eligible if s in history and history[s]["min_date"]<=d<=history[s]["max_date"]])
        missing=sorted(set(eligible)-set(covered))
        pct=len(covered)/len(eligible)*100 if eligible else 0
        passed=bool(eligible and pct>=MIN_COVERAGE)
        all_pass=all_pass and passed
        dates[d]={"pit_symbols":len(eligible),"price_symbols_covered":len(covered),"coverage_pct":round(pct,4),"pass":passed,"missing_symbols":missing}

    # Missingness audit across observed market dates; no fill is applied.
    market_dates=sorted({d for ds in observed.values() for d in ds})
    expected=0; actual=0; missing_by_symbol={}
    by_symbol=defaultdict(list)
    for i in intervals:
        if i.get("symbol"): by_symbol[str(i["symbol"])].append(i)
    for s,ints in by_symbol.items():
        exp=[d for d in market_dates if any(_contains(i,d) for i in ints)]
        miss=[d for d in exp if d not in observed.get(s,set())]
        expected+=len(exp); actual+=len(exp)-len(miss)
        if miss:
            buckets=defaultdict(int)
            for d in miss: buckets[d[:7]]+=1
            missing_by_symbol[s]=dict(sorted(buckets.items()))

    status="READY_FOR_W1_CANONICAL_REPLAY" if all_pass and not duplicates and not nonadjusted else "BLOCKED_PRICE_HISTORY_COVERAGE"
    report={
        "schema_version":"SWING_PIT_PRICE_COVERAGE_2.0",
        "status":status,
        "pit_intervals":len(intervals),
        "pit_unique_symbols":len({str(i.get("symbol")) for i in intervals if i.get("symbol")}),
        "price_symbols_available":len(history),
        "audit_dates":dates,
        "symbol_day_expected":expected,
        "symbol_day_observed":actual,
        "symbol_day_coverage_pct":round(actual/expected*100,4) if expected else 0,
        "duplicates":duplicates,
        "nonadjusted_symbols":nonadjusted,
        "failed_symbols":failed,
        "quarantined_symbols":quarantined,
        "empty_symbols":sorted(set(empty)),
        "shard_reports":len(shard_reports),
        "missingness_by_symbol":missing_by_symbol,
        "governance":{
            "current_universe_substitution_forbidden":True,
            "forward_fill":False,
            "price_adjustment":"confirmed corporate-event reference ratio, backward adjusted",
            "volume_adjusted":False,
            "market_transfer":"exchange resolved from canonical PIT interval per bar date",
        },
    }
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    (out/"coverage_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# W3 Swing Canonical PIT Daily Coverage","",f"- Status: **{status}**",f"- PIT unique symbols: {report['pit_unique_symbols']:,}",f"- Price symbols available: {len(history):,}",f"- Symbol-day coverage: {report['symbol_day_coverage_pct']:.2f}%","","| Audit date | PIT | Covered | Coverage | Gate |","|---|---:|---:|---:|---|"]
    for d,x in dates.items():
        lines.append(f"| {d} | {x['pit_symbols']:,} | {x['price_symbols_covered']:,} | {x['coverage_pct']:.2f}% | {'PASS' if x['pass'] else 'BLOCKED'} |")
    lines += ["",f"- Duplicate rows: {len(duplicates)}",f"- Failed symbols: {len(failed)}",f"- Quarantined symbols: {len(quarantined)}",f"- Empty symbols: {len(set(empty))}","- Missing bars are not forward-filled."]
    (out/"coverage_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    if status!="READY_FOR_W1_CANONICAL_REPLAY":
        raise SystemExit(2)

if __name__=="__main__": main()
