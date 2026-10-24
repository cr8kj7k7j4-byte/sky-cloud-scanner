from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.incident_response import Incident, required_action
from src.degradation_controller import system_mode, recovery_gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incident", required=True, help="incident JSON file")
    ap.add_argument("--out", default="research_output/incident_runbook.json")
    args = ap.parse_args()

    payload = json.loads(Path(args.incident).read_text(encoding="utf-8"))
    incident = Incident(**payload["incident"])
    action = required_action(incident)

    health = payload.get("health", {})
    degradation = system_mode(
        official_data_ok=health.get("official_data_ok", False),
        quote_freshness_ok=health.get("quote_freshness_ok", False),
        risk_engine_ok=health.get("risk_engine_ok", False),
        execution_costs_ok=health.get("execution_costs_ok", False),
        monitoring_ok=health.get("monitoring_ok", False),
        state_store_ok=health.get("state_store_ok", False),
        secrets_ok=health.get("secrets_ok", False),
    )

    recovery = recovery_gate(**payload.get("recovery", {}))

    report = {
        "incident": incident.to_dict(),
        "required_action": action,
        "degradation": degradation,
        "recovery": recovery,
        "live_order_allowed": False,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
