from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

def _d(value):
    return date.fromisoformat(str(value)[:10])

def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def load_expected(interval_path: str, from_date: str, to_date: str) -> dict:
    obj=json.loads(Path(interval_path).read_text(encoding="utf-8"))
    rows=obj.get("intervals") if isinstance(obj,dict) else obj
    start=_d(from_date); end=_d(to_date)
    out={}
    for row in rows or []:
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
            out[key]={"from":a,"to":b}
        else:
            prev["from"]=min(prev["from"],a)
            prev["to"]=max(prev["to"],b)
    return out

def _collect_legacy_files(root: Path):
    # Supports extracted shard directories and nested shard tar extractions.
    return sorted(
        p for p in root.rglob("*_5m.json")
        if p.is_file()
    )

def reconcile_cache(
    *,
    pit_intervals: str,
    legacy_root: str,
    out_root: str,
    from_date: str,
    to_date: str,
    source_run_id: int | None=None,
    source_artifact_id: int | None=None,
) -> dict:
    expected=load_expected(pit_intervals,from_date,to_date)
    legacy=Path(legacy_root)
    out=Path(out_root)
    out.mkdir(parents=True,exist_ok=True)

    source_files=_collect_legacy_files(legacy)
    output_index={}
    stale_files=[]
    parse_errors=[]
    conflicts=[]
    duplicate_bars=0
    bars_seen=0
    bars_kept=0
    bars_dropped_outside_membership=0

    # Multiple old files/chunks can belong to the same symbol. Merge causally
    # by timestamp and reject conflicting payloads for the same timestamp.
    merged=defaultdict(dict)
    meta={}

    for p in source_files:
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            symbol=str(obj.get("symbol") or "")
            exchange=str(obj.get("exchange") or "")
            key=(exchange,symbol)
            if key not in expected:
                stale_files.append({
                    "file":str(p),
                    "symbol":symbol,
                    "exchange":exchange,
                    "reason":"NOT_IN_CORRECTED_PIT_UNION",
                })
                continue
            a=expected[key]["from"]; b=expected[key]["to"]
            meta[key]={
                "symbol":symbol,
                "exchange":exchange,
                "history_required_from":a.isoformat(),
                "history_required_to":b.isoformat(),
            }
            for bar in obj.get("data") or []:
                bars_seen+=1
                ts=str(bar.get("date") or "")
                if not ts:
                    continue
                day=_d(ts)
                if day<a or day>b:
                    bars_dropped_outside_membership+=1
                    continue
                normalized=json.dumps(bar,sort_keys=True,ensure_ascii=False,separators=(",",":"))
                prev=merged[key].get(ts)
                if prev is not None:
                    duplicate_bars+=1
                    if prev["normalized"]!=normalized:
                        conflicts.append({
                            "symbol":symbol,"exchange":exchange,
                            "timestamp":ts,
                            "first_file":prev["file"],
                            "second_file":str(p),
                        })
                    continue
                merged[key][ts]={
                    "bar":bar,
                    "normalized":normalized,
                    "file":str(p),
                }
                bars_kept+=1
        except Exception as exc:
            parse_errors.append({
                "file":str(p),
                "error":f"{type(exc).__name__}: {exc}",
            })

    if conflicts:
        return {
            "schema_version":"PIT_HISTORY_CACHE_RECONCILE_V1_0",
            "status":"FAIL",
            "reason":"CONFLICTING_DUPLICATE_BARS",
            "conflicts":conflicts[:500],
            "parse_errors":parse_errors[:500],
        }

    for key,by_ts in sorted(merged.items()):
        exchange,symbol=key
        rows=[by_ts[k]["bar"] for k in sorted(by_ts)]
        target=out/exchange/symbol/f"{from_date}_{to_date}_5m.json"
        target.parent.mkdir(parents=True,exist_ok=True)
        payload={
            **meta[key],
            "timeframe":"5",
            "from":from_date,
            "to":to_date,
            "source_lineage":{
                "type":"RECONCILED_LEGACY_RAW_CACHE",
                "source_run_id":source_run_id,
                "source_artifact_id":source_artifact_id,
                "pit_intervals_sha256":_sha256(Path(pit_intervals)),
                "reconciled_against_corrected_pit":True,
            },
            "data":rows,
        }
        target.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
        output_index[f"{exchange}:{symbol}"]={
            "path":str(target),
            "bars":len(rows),
            "sha256":_sha256(target),
            "history_required_from":meta[key]["history_required_from"],
            "history_required_to":meta[key]["history_required_to"],
        }

    expected_keys=set(expected)
    observed_keys=set(merged)
    missing_keys=sorted(expected_keys-observed_keys)

    report={
        "schema_version":"PIT_HISTORY_CACHE_RECONCILE_V1_0",
        "status":"PASS" if not parse_errors and not conflicts else "FAIL",
        "from_date":from_date,
        "to_date":to_date,
        "source_run_id":source_run_id,
        "source_artifact_id":source_artifact_id,
        "pit_intervals_sha256":_sha256(Path(pit_intervals)),
        "source_files":len(source_files),
        "corrected_expected_symbols":len(expected_keys),
        "symbols_materialized":len(observed_keys),
        "symbol_cache_coverage":round(len(observed_keys)/len(expected_keys),6) if expected_keys else 0.0,
        "missing_corrected_symbols":[
            {"exchange":ex,"symbol":sym} for ex,sym in missing_keys
        ][:1000],
        "stale_source_files_dropped":len(stale_files),
        "stale_source_files":stale_files[:500],
        "bars_seen":bars_seen,
        "bars_kept":bars_kept,
        "bars_dropped_outside_corrected_membership":bars_dropped_outside_membership,
        "duplicate_bar_count":duplicate_bars,
        "conflicting_duplicate_count":len(conflicts),
        "parse_errors":parse_errors[:500],
        "outputs":output_index,
        "governance":{
            "new_external_download_performed":False,
            "legacy_cache_is_raw_market_data_only":True,
            "corrected_pit_membership_applied":True,
            "stale_symbols_are_dropped":True,
            "out_of_membership_bars_are_dropped":True,
            "conflicting_duplicates_fail_closed":True,
        },
    }
    (out/"reconciliation_manifest.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pit-intervals",required=True)
    ap.add_argument("--legacy-root",required=True)
    ap.add_argument("--out-root",required=True)
    ap.add_argument("--from-date",required=True)
    ap.add_argument("--to-date",required=True)
    ap.add_argument("--source-run-id",type=int)
    ap.add_argument("--source-artifact-id",type=int)
    args=ap.parse_args()
    report=reconcile_cache(
        pit_intervals=args.pit_intervals,
        legacy_root=args.legacy_root,
        out_root=args.out_root,
        from_date=args.from_date,
        to_date=args.to_date,
        source_run_id=args.source_run_id,
        source_artifact_id=args.source_artifact_id,
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"]!="PASS":
        raise SystemExit(1)

if __name__=="__main__":
    main()
