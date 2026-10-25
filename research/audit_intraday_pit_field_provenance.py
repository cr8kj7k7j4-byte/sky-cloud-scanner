from __future__ import annotations
import argparse,json
from pathlib import Path

PASSLIKE={"PASS","ENGINE_READY"}
BLOCKING={"BLOCKED","ENGINE_READY_INPUT_BLOCKED","PENDING_SOURCE_COVERAGE"}

def audit_registry(registry: dict) -> dict:
    rows=[]
    for domain,item in (registry.get("domains") or {}).items():
        rows.append({
            "domain":domain,
            "status":item.get("status","UNKNOWN"),
            "field_count":len(item.get("fields") or []),
            "fields":item.get("fields") or [],
            "required_source":item.get("required_source"),
            "reason":item.get("reason"),
        })
    blocked=[x for x in rows if x["status"] in BLOCKING]
    partial=[x for x in rows if x["status"] not in PASSLIKE and x["status"] not in BLOCKING]
    field_total=sum(x["field_count"] for x in rows)
    field_pass=sum(x["field_count"] for x in rows if x["status"] in PASSLIKE)
    return {
        "schema_version":"INTRADAY_PIT_FIELD_PROVENANCE_AUDIT_V1_0",
        "domain_count":len(rows),
        "field_count":field_total,
        "pass_field_count":field_pass,
        "engine/source_ready_share":round(field_pass/max(field_total,1),6),
        "domains":rows,
        "blocking_domains":[x["domain"] for x in blocked],
        "partial_domains":[x["domain"] for x in partial],
        "status":"PASS" if not blocked and not partial else "DATA_BLOCKED",
        "production_change":False,
        "note":"Coverage here is source/provenance readiness, not empirical dataset row coverage and not strategy efficacy."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",required=True)
    ap.add_argument("--out",default="research_output/intraday_pit_field_provenance_audit.json")
    args=ap.parse_args()
    obj=json.loads(Path(args.registry).read_text(encoding="utf-8"))
    report=audit_registry(obj)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
