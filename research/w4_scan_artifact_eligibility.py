from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LEDGER_START="2026-10-24T23:28:08Z"


def _parse_dt(value):
    if not value:
        return None
    try:
        dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def audit_scan_artifacts(root: str, ledger_start: str=DEFAULT_LEDGER_START) -> dict:
    base=Path(root)
    start=_parse_dt(ledger_start)
    runs={}
    malformed=[]
    files=sorted(
        p for p in base.rglob("*.json")
        if "paper" in {part.lower() for part in p.parts}
    )

    for p in files:
        try:
            payload=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            malformed.append({"path":str(p),"reason":f"{type(exc).__name__}: {exc}"})
            continue
        rows=payload.get("records") if isinstance(payload,dict) else None
        if not isinstance(rows,list):
            malformed.append({"path":str(p),"reason":"records_not_list"})
            continue

        run_id=""
        # Canonical downloaded artifact layout: shadow_history/<run_id>/output/paper/*.json
        parts=list(p.parts)
        if "shadow_history" in parts:
            idx=parts.index("shadow_history")
            if idx+1 < len(parts):
                run_id=str(parts[idx+1])
        if not run_id and rows:
            run_id=str((rows[0] or {}).get("run_id") or "")
        if not run_id:
            run_id=f"unknown:{p}"

        rec=runs.setdefault(run_id,{
            "run_id":run_id,
            "files":0,
            "records":0,
            "eligible_records":0,
            "post_ledger_records":0,
            "valid_observation_records":0,
        })
        rec["files"]+=1
        rec["records"]+=len(rows)

        for row in rows:
            if not isinstance(row,dict):
                continue
            observed=_parse_dt(row.get("observed_at") or row.get("observation_timestamp"))
            if observed is None:
                continue
            rec["valid_observation_records"]+=1
            if start is None or observed>=start:
                rec["post_ledger_records"]+=1
                symbol=str(row.get("symbol") or "").strip()
                if symbol:
                    rec["eligible_records"]+=1

    ordered=sorted(runs.values(),key=lambda x:x["run_id"])
    eligible=[x for x in ordered if x["eligible_records"]>0]
    empty=[x for x in ordered if x["eligible_records"]==0]

    return {
        "schema_version":"W4_SCAN_ARTIFACT_ELIGIBILITY_V1_0",
        "ledger_start":ledger_start,
        "paper_files_scanned":len(files),
        "run_count":len(ordered),
        "eligible_run_count":len(eligible),
        "eligible_record_count":sum(x["eligible_records"] for x in eligible),
        "eligible_run_ids":[x["run_id"] for x in eligible],
        "ineligible_or_empty_runs":[x["run_id"] for x in empty],
        "runs":ordered,
        "malformed_files":malformed,
        "status":"PASS" if not malformed else "WARN",
        "governance":{
            "workflow_success_alone_is_not_eligible_evidence":True,
            "nonempty_post_ledger_paper_record_required":True,
            "holiday_or_empty_scan_counts_as_eligible":False,
            "production_change":False,
        },
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="shadow_history")
    ap.add_argument("--ledger-start",default=DEFAULT_LEDGER_START)
    ap.add_argument("--out",default="research_output/w4_scan_eligibility.json")
    args=ap.parse_args()
    report=audit_scan_artifacts(args.root,args.ledger_start)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
