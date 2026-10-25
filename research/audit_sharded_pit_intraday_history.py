from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

COVERAGE_GATE=0.95


def _d(value):
    return date.fromisoformat(str(value)[:10])


def load_expected(interval_path: str, from_date: str, to_date: str):
    obj=json.loads(Path(interval_path).read_text(encoding="utf-8"))
    intervals=obj.get("intervals") if isinstance(obj,dict) else obj
    start=_d(from_date); end=_d(to_date)
    out={}
    for row in intervals or []:
        symbol=str(row.get("symbol") or "")
        exchange=str(row.get("exchange") or "")
        if not symbol or exchange not in {"TWSE","TPEx"}:
            continue
        a=max(_d(row["listed_from"]),start)
        raw_end=row.get("listed_to")
        b=min(_d(raw_end) if raw_end else end,end)
        if a>end or b<start:
            continue
        key=(exchange,symbol)
        prev=out.get(key)
        if prev is None:
            out[key]=(a,b)
        else:
            out[key]=(min(prev[0],a),max(prev[1],b))
    return out


def audit_sharded_history(
    *,
    pit_intervals: str,
    history_root: str,
    from_date: str,
    to_date: str,
) -> dict:
    expected=load_expected(pit_intervals,from_date,to_date)
    root=Path(history_root)
    observed_by_date=defaultdict(set)
    symbol_bars=defaultdict(int)
    duplicate_bars=0
    out_of_membership=0
    parse_errors=[]
    transport_files=0

    for p in root.rglob("*_5m.json"):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            symbol=str(obj.get("symbol") or "")
            exchange=str(obj.get("exchange") or "")
            key=(exchange,symbol)
            if key not in expected:
                # Shard provenance should never contain symbols outside PIT union.
                parse_errors.append({"file":str(p),"reason":"SYMBOL_NOT_IN_PIT_UNION"})
                continue
            a,b=expected[key]
            seen=set()
            for bar in obj.get("data") or []:
                ts=str(bar.get("date") or "")
                if not ts:
                    continue
                if ts in seen:
                    duplicate_bars+=1
                seen.add(ts)
                day=_d(ts)
                if day<a or day>b:
                    out_of_membership+=1
                    continue
                observed_by_date[day].add(key)
                symbol_bars[key]+=1
            transport_files+=1
        except Exception as exc:
            parse_errors.append({
                "file":str(p),
                "reason":f"{type(exc).__name__}: {exc}",
            })

    # Use observed trading dates. Missing a whole market day from every symbol
    # cannot be distinguished from a true exchange holiday without the governed
    # market calendar; that calendar audit remains a separate P0-DATA input.
    dates=sorted(observed_by_date)
    daily=[]
    expected_symbol_days=0
    observed_symbol_days=0
    for day in dates:
        exp={k for k,(a,b) in expected.items() if a<=day<=b}
        obs=observed_by_date[day] & exp
        expected_symbol_days+=len(exp)
        observed_symbol_days+=len(obs)
        daily.append({
            "date":day.isoformat(),
            "expected_symbols":len(exp),
            "observed_symbols":len(obs),
            "coverage":round(len(obs)/len(exp),6) if exp else 0.0,
            "missing_count":len(exp)-len(obs),
        })

    coverage=observed_symbol_days/expected_symbol_days if expected_symbol_days else 0.0
    symbols_with_bars=sum(1 for k in expected if symbol_bars.get(k,0)>0)
    symbol_coverage=symbols_with_bars/len(expected) if expected else 0.0
    report={
        "schema_version":"SHARDED_PIT_INTRADAY_COVERAGE_V1_0",
        "from_date":from_date,
        "to_date":to_date,
        "expected_symbols":len(expected),
        "symbols_with_bars":symbols_with_bars,
        "symbol_coverage":round(symbol_coverage,6),
        "trading_dates_observed":len(dates),
        "expected_symbol_days":expected_symbol_days,
        "observed_symbol_days":observed_symbol_days,
        "symbol_day_coverage":round(coverage,6),
        "minimum_daily_coverage":round(min((x["coverage"] for x in daily),default=0.0),6),
        "duplicate_bar_count":duplicate_bars,
        "out_of_membership_bar_count":out_of_membership,
        "parse_errors":parse_errors[:500],
        "chunk_files":transport_files,
        "worst_dates":sorted(daily,key=lambda x:x["coverage"])[:30],
        "gate_threshold":COVERAGE_GATE,
        "status":"PASS" if (
            symbol_coverage>=COVERAGE_GATE
            and coverage>=COVERAGE_GATE
            and duplicate_bars==0
            and out_of_membership==0
            and not parse_errors
        ) else "FAIL",
        "governance":{
            "pit_interval_clamp_required":True,
            "current_universe_backward_sampling":False,
            "suspension_exemptions":False,
            "market_calendar_required_for_zero-observation-day_audit":True,
        },
    }
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pit-intervals",required=True)
    ap.add_argument("--history-root",required=True)
    ap.add_argument("--from-date",required=True)
    ap.add_argument("--to-date",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    report=audit_sharded_history(
        pit_intervals=args.pit_intervals,
        history_root=args.history_root,
        from_date=args.from_date,
        to_date=args.to_date,
    )
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
