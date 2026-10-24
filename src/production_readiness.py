from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ReadinessDomain:
    name: str
    weight: int
    passed: bool
    critical: bool = False
    detail: str = ""

    def to_dict(self):
        return asdict(self)


def score_readiness(domains):
    rows = list(domains or [])
    total = sum(max(0, int(x.weight)) for x in rows)
    earned = sum(max(0, int(x.weight)) for x in rows if x.passed)
    score = round(100.0 * earned / total, 1) if total else 0.0

    failed = [x.name for x in rows if not x.passed]
    critical_failed = [x.name for x in rows if x.critical and not x.passed]

    return {
        "score": score,
        "meaning": "Production engineering/governance readiness only; not win rate or profit probability.",
        "all_passed": not failed,
        "critical_failed": critical_failed,
        "failed_domains": failed,
        "release_review_allowed": not failed and score == 100.0,
        "automatic_live_release_allowed": False,
        "domains": [x.to_dict() for x in rows],
    }


def default_production_domains(
    *,
    data_quality=False,
    official_data_chain=False,
    feature_schema=False,
    strategy_validation=False,
    model_validation=False,
    risk_engine=False,
    execution_costs=False,
    monitoring=False,
    shadow_trading=False,
    champion_challenger=False,
    registry_governance=False,
    rollback=False,
    observability=False,
    security_secrets=False,
):
    return [
        ReadinessDomain("P0-DATA Data Quality", 8, data_quality, True),
        ReadinessDomain("Official Market Data Chain", 8, official_data_chain, True),
        ReadinessDomain("P0-F Feature Schema/Version", 6, feature_schema, False),
        ReadinessDomain("P0-S/P0-C Strategy Validation", 10, strategy_validation, True),
        ReadinessDomain("P0-ML Model Validation", 8, model_validation, False),
        ReadinessDomain("P0-R Risk Engine", 10, risk_engine, True),
        ReadinessDomain("P0-X Execution Cost Model", 8, execution_costs, True),
        ReadinessDomain("P0-A Monitoring/Alert", 6, monitoring, True),
        ReadinessDomain("Shadow/Paper Trading", 8, shadow_trading, True),
        ReadinessDomain("Champion vs Challenger", 6, champion_challenger, False),
        ReadinessDomain("P0-G Registry/Governance", 6, registry_governance, True),
        ReadinessDomain("Rollback Drill", 6, rollback, True),
        ReadinessDomain("Observability/Incident Readiness", 5, observability, True),
        ReadinessDomain("Secrets/Security Hygiene", 5, security_secrets, True),
    ]
