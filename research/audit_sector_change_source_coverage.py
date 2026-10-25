from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EXCHANGES=("TWSE","TPEx")
VERIFIED_STATUSES={"VERIFIED","VERIFIED_SOURCE_URL_PENDING_PARSER"}


def audit_registry(registry: dict) -> dict:
    start_year=int(str(registry.get("governed_window_start","2023-01-01"))[:4])
    # Current project horizon is explicit in the registry entries; do not infer future years.
    present_years=sorted({
        int(y)
        for ex in registry.get("exchanges",{}).values()
        for y in (ex.get("years") or {}).keys()
    })
    end_year=max(present_years) if present_years else start_year
    required_years=list(range(start_year,end_year+1))

    gaps=[]
    details=[]
    for exchange in REQUIRED_EXCHANGES:
        ex=registry.get("exchanges",{}).get(exchange,{})
        years=ex.get("years") or {}
        for year in required_years:
            item=years.get(str(year))
            status=(item or {}).get("status","MISSING")
            verified=status in VERIFIED_STATUSES
            details.append({
                "exchange":exchange,"year":year,"status":status,
                "verified":verified,
                "source_url":(item or {}).get("source_url"),
                "effective_date":(item or {}).get("effective_date"),
                "notice_no":(item or {}).get("notice_no"),
            })
            if not verified:
                gaps.append({
                    "exchange":exchange,"year":year,"status":status,
                    "reason":(item or {}).get("reason","MISSING_SOURCE_REGISTRY_ENTRY"),
                })

    return {
        "schema_version":"SECTOR_CHANGE_SOURCE_COVERAGE_AUDIT_V1_0",
        "governed_years":required_years,
        "expected_exchange_years":len(REQUIRED_EXCHANGES)*len(required_years),
        "verified_exchange_years":sum(1 for x in details if x["verified"]),
        "coverage":round(
            sum(1 for x in details if x["verified"])/max(len(details),1),6
        ),
        "details":details,
        "gaps":gaps,
        "status":"PASS" if not gaps else "BLOCKED",
        "governance":{
            "missing_year_is_not_zero_changes":True,
            "current_anchor_not_historical_pit":True,
            "all_exchange_years_must_be_verified":True,
        },
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",required=True)
    ap.add_argument("--out",default="research_output/sector_change_source_coverage.json")
    args=ap.parse_args()
    registry=json.loads(Path(args.registry).read_text(encoding="utf-8"))
    report=audit_registry(registry)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
