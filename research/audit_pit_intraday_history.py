from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

COVERAGE_GATE=0.95


def _d(x):
    return date.fromisoformat(str(x)[:10])


def audit(manifest: dict, history_dir: str, summary: list[dict] | None=None) -> dict:
    sample=list(manifest.get("sample") or [])
    expected_ranges={
        str(x["symbol"]):(_d(x["history_required_from"]),_d(x["history_required_to"]),str(x.get("exchange") or ""))
        for x in sample
    }
    history=Path(history_dir)
    observed_by_date=defaultdict(set)
    symbol_bar_counts={}
    parse_errors=[]
    duplicate_bars=0
    out_of_membership_bars=0

    for symbol,(start,end,_) in expected_ranges.items():
        p=history/f"{symbol}_5.json"
        if not p.exists():
            symbol_bar_counts[symbol]=0
            continue
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            bars=obj.get("data") or []
            symbol_bar_counts[symbol]=len(bars)
            seen=set()
            for b in bars:
                ts=str(b.get("date") or "")
                if not ts:
                    continue
                key=ts
                if key in seen:
                    duplicate_bars+=1
                seen.add(key)
                day=_d(ts)
                if day<start or day>end:
                    out_of_membership_bars+=1
                    continue
                observed_by_date[day].add(symbol)
        except Exception as exc:
            parse_errors.append({"symbol":symbol,"error":f"{type(exc).__name__}: {exc}"})
            symbol_bar_counts[symbol]=0

    trading_dates=sorted(observed_by_date)
    expected_symbol_days=0
    observed_symbol_days=0
    daily=[]
    for day in trading_dates:
        expected={
            s for s,(a,b,_) in expected_ranges.items()
            if a<=day<=b
        }
        observed=observed_by_date.get(day,set()) & expected
        exp=len(expected); obs=len(observed)
        expected_symbol_days+=exp
        observed_symbol_days+=obs
        daily.append({
            "date":day.isoformat(),
            "expected_symbols":exp,
            "observed_symbols":obs,
            "coverage":round(obs/exp,6) if exp else 0.0,
            "missing_count":exp-obs,
        })

    coverage=(
        observed_symbol_days/expected_symbol_days
        if expected_symbol_days else 0.0
    )
    empty_symbols=sorted([s for s,n in symbol_bar_counts.items() if n==0])
    failed_downloads=[
        x for x in (summary or []) if not x.get("ok")
    ]
    report={
        "schema_version":"PIT_INTRADAY_HISTORY_COVERAGE_AUDIT_V1_0",
        "manifest_method":manifest.get("method"),
        "manifest_symbols":len(expected_ranges),
        "trading_dates":len(trading_dates),
        "expected_symbol_days":expected_symbol_days,
        "observed_symbol_days":observed_symbol_days,
        "symbol_day_coverage":round(coverage,6),
        "minimum_daily_coverage":round(min((x["coverage"] for x in daily),default=0.0),6),
        "median_daily_coverage":round(
            sorted([x["coverage"] for x in daily])[len(daily)//2]
            if daily else 0.0,6
        ),
        "empty_symbol_count":len(empty_symbols),
        "empty_symbols":empty_symbols[:500],
        "failed_download_count":len(failed_downloads),
        "failed_downloads":failed_downloads[:200],
        "parse_errors":parse_errors[:200],
        "duplicate_bar_count":duplicate_bars,
        "out_of_membership_bar_count":out_of_membership_bars,
        "worst_dates":sorted(daily,key=lambda x:x["coverage"])[:30],
        "gate_threshold":COVERAGE_GATE,
        "status":"PASS" if (
            coverage>=COVERAGE_GATE
            and not parse_errors
            and duplicate_bars==0
            and out_of_membership_bars==0
        ) else "FAIL",
        "governance":{
            "universe_source":"PIT_MEMBERSHIP_INTERVALS",
            "current_universe_backward_sampling":False,
            "suspension_adjustment_applied":False,
            "note":"Missing bars are conservatively treated as missing evidence. Suspension-specific exemptions require a verified suspension ledger.",
        },
    }
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--download-summary")
    ap.add_argument("--out",default="research_output/pit_history_coverage_audit.json")
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    summary=(
        json.loads(Path(args.download_summary).read_text(encoding="utf-8"))
        if args.download_summary and Path(args.download_summary).exists()
        else []
    )
    report=audit(manifest,args.history_dir,summary)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
