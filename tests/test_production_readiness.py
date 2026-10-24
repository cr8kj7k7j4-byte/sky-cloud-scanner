import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.production_readiness import default_production_domains, score_readiness
from src.release_gate import release_gate


def main():
    partial = score_readiness(default_production_domains(
        data_quality=True,
        official_data_chain=False,
        feature_schema=True,
        strategy_validation=True,
        model_validation=True,
        risk_engine=True,
        execution_costs=True,
        monitoring=True,
        shadow_trading=True,
        champion_challenger=True,
        registry_governance=True,
        rollback=True,
        observability=True,
        security_secrets=True,
    ))
    assert partial["score"] < 100
    assert partial["release_review_allowed"] is False
    assert "Official Market Data Chain" in partial["critical_failed"]

    full = score_readiness(default_production_domains(
        data_quality=True,
        official_data_chain=True,
        feature_schema=True,
        strategy_validation=True,
        model_validation=True,
        risk_engine=True,
        execution_costs=True,
        monitoring=True,
        shadow_trading=True,
        champion_challenger=True,
        registry_governance=True,
        rollback=True,
        observability=True,
        security_secrets=True,
    ))
    assert full["score"] == 100.0
    assert full["release_review_allowed"] is True
    assert full["automatic_live_release_allowed"] is False

    gate = release_gate(
        full,
        ci_passed=True,
        paper_sample_sufficient=True,
        rollback_drill_passed=True,
        incident_runbook_present=True,
        manual_approval=False,
    )
    assert gate["release_review_passed"] is False
    assert "manual_approval" in gate["failed_checks"]
    assert gate["production_release_allowed"] is False

    approved = release_gate(
        full,
        ci_passed=True,
        paper_sample_sufficient=True,
        rollback_drill_passed=True,
        incident_runbook_present=True,
        manual_approval=True,
    )
    assert approved["release_review_passed"] is True
    assert approved["production_release_allowed"] is False

    print("PASS Production Readiness Scorecard + Release Gate tests")


if __name__ == "__main__":
    main()
