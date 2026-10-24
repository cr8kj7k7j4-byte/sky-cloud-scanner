from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class RollbackDrill:
    from_version: str
    to_version: str
    config_restored: bool
    rules_restored: bool
    feature_schema_restored: bool
    model_restored: bool
    risk_policy_restored: bool
    monitoring_restored: bool
    state_store_restored: bool
    smoke_tests_passed: bool
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def evaluate_rollback_drill(drill):
    d = drill if isinstance(drill, RollbackDrill) else RollbackDrill(**drill)

    checks = {
        "config_restored": d.config_restored,
        "rules_restored": d.rules_restored,
        "feature_schema_restored": d.feature_schema_restored,
        "model_restored": d.model_restored,
        "risk_policy_restored": d.risk_policy_restored,
        "monitoring_restored": d.monitoring_restored,
        "state_store_restored": d.state_store_restored,
        "smoke_tests_passed": d.smoke_tests_passed,
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "rollback_drill_passed": not failed,
        "from_version": d.from_version,
        "to_version": d.to_version,
        "checks": checks,
        "failed_checks": failed,
        "production_reactivation_allowed": False,
        "note": (
            "Rollback drill success only proves restoration capability. "
            "Production reactivation remains manual and separate."
        ),
    }
