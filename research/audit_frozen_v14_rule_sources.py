from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED={"FROZEN_CANONICAL_IMPLEMENTATION","HISTORICAL_SNAPSHOT"}

def audit_registry(registry: dict) -> dict:
    rules=list(registry.get("rules") or [])
    unresolved=[
        {
            "rule":x.get("rule"),
            "status":x.get("status"),
            "reason":x.get("reason"),
            "components":x.get("components") or [],
        }
        for x in rules
        if str(x.get("status")) not in ALLOWED
    ]
    return {
        "schema_version":"SKY_DAY_V14_FROZEN_RULE_SOURCE_AUDIT_V1_0",
        "strategy_id":registry.get("strategy_id"),
        "rule_count":len(rules),
        "resolved_count":len(rules)-len(unresolved),
        "coverage":round((len(rules)-len(unresolved))/max(len(rules),1),6),
        "unresolved":unresolved,
        "status":"PASS" if rules and not unresolved else "BLOCKED",
        "deterministic_historical_decision_replay_allowed":bool(rules and not unresolved),
        "production_change":False,
        "note":"This gate validates replay provenance only; it does not judge rule profitability.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry",required=True)
    ap.add_argument("--out",default="research_output/frozen_v14_rule_source_audit.json")
    args=ap.parse_args()
    obj=json.loads(Path(args.registry).read_text(encoding="utf-8"))
    report=audit_registry(obj)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
