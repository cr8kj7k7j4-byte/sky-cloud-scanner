import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.incident_response import Incident, required_action
from src.degradation_controller import system_mode, recovery_gate
from src.rollback_drill import RollbackDrill, evaluate_rollback_drill


def main():
    sev1 = Incident(
        incident_type="RISK_ENGINE_ANOMALY",
        severity="SEV1",
        detected_at="2026-10-25T09:30:00+08:00",
        source="P0-R",
        detail="unexpected risk-state mismatch",
        affected_modules=("P0-R", "P0-X"),
    )
    action = required_action(sev1)
    assert action["new_entries_allowed"] is False
    assert action["rollback_required"] is True

    degraded = system_mode(
        official_data_ok=True,
        quote_freshness_ok=True,
        risk_engine_ok=False,
        execution_costs_ok=True,
        monitoring_ok=True,
        state_store_ok=True,
        secrets_ok=True,
    )
    assert degraded["mode"] == "LOCKDOWN"
    assert degraded["new_entries_allowed"] is False

    recovery = recovery_gate(
        incident_resolved=True,
        data_freshness_restored=True,
        risk_engine_verified=True,
        execution_costs_verified=True,
        monitoring_verified=True,
        state_store_verified=True,
        rollback_or_fix_verified=True,
        manual_approval=False,
    )
    assert recovery["recovery_review_passed"] is False
    assert "manual_approval" in recovery["failed_checks"]
    assert recovery["resume_new_entries_allowed"] is False

    drill = RollbackDrill(
        from_version="2.2.0",
        to_version="2.1.0",
        config_restored=True,
        rules_restored=True,
        feature_schema_restored=True,
        model_restored=True,
        risk_policy_restored=True,
        monitoring_restored=True,
        state_store_restored=True,
        smoke_tests_passed=True,
    )
    result = evaluate_rollback_drill(drill)
    assert result["rollback_drill_passed"] is True
    assert result["production_reactivation_allowed"] is False

    print("PASS Operational Runbook + Rollback Drill + Incident Response tests")


if __name__ == "__main__":
    main()
