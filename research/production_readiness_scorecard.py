from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.production_readiness import default_production_domains, score_readiness
from src.release_gate import release_gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, help="JSON booleans for readiness domains")
    ap.add_argument("--out", default="research_output/production_readiness.json")
    args = ap.parse_args()

    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    domains = default_production_domains(
        data_quality=evidence.get("data_quality", False),
        official_data_chain=evidence.get("official_data_chain", False),
        feature_schema=evidence.get("feature_schema", False),
        strategy_validation=evidence.get("strategy_validation", False),
        model_validation=evidence.get("model_validation", False),
        risk_engine=evidence.get("risk_engine", False),
        execution_costs=evidence.get("execution_costs", False),
        monitoring=evidence.get("monitoring", False),
        shadow_trading=evidence.get("shadow_trading", False),
        champion_challenger=evidence.get("champion_challenger", False),
        registry_governance=evidence.get("registry_governance", False),
        rollback=evidence.get("rollback", False),
        observability=evidence.get("observability", False),
        security_secrets=evidence.get("security_secrets", False),
    )
    readiness = score_readiness(domains)
    gate = release_gate(
        readiness,
        ci_passed=evidence.get("ci_passed", False),
        paper_sample_sufficient=evidence.get("paper_sample_sufficient", False),
        rollback_drill_passed=evidence.get("rollback_drill_passed", False),
        incident_runbook_present=evidence.get("incident_runbook_present", False),
        manual_approval=evidence.get("manual_approval", False),
    )
    report = {"readiness": readiness, "release_gate": gate}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
