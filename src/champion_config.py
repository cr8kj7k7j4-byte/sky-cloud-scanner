from __future__ import annotations

CORE_RULE_IDS = (
    "market_gate",
    "sector_rs_gate",
    "anti_chase_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "rr_gate",
)


def build_champion_config(
    *,
    config_id,
    version,
    rule_versions,
    model_version=None,
    feature_schema_version=None,
    rollback_to=None,
    effective_from=None,
    notes="",
):
    missing = [r for r in CORE_RULE_IDS if r not in rule_versions]
    extra = [r for r in rule_versions if r not in CORE_RULE_IDS]
    if missing:
        raise ValueError(f"missing core rules: {missing}")
    if extra:
        raise ValueError(f"unknown rules: {extra}")

    return {
        "config_id": config_id,
        "version": version,
        "rules": dict(rule_versions),
        "model_version": model_version,
        "feature_schema_version": feature_schema_version,
        "rollback_to": rollback_to,
        "effective_from": effective_from,
        "notes": notes,
    }


def promotion_readiness(
    *,
    walk_forward=False,
    oos=False,
    cost_stress=False,
    leakage_check=False,
    survivorship_review=False,
    regime_stability=False,
    paper_trade=False,
    sample_sufficient=False,
):
    checks = {
        "walk_forward": bool(walk_forward),
        "oos": bool(oos),
        "cost_stress": bool(cost_stress),
        "leakage_check": bool(leakage_check),
        "survivorship_review": bool(survivorship_review),
        "regime_stability": bool(regime_stability),
        "paper_trade": bool(paper_trade),
        "sample_sufficient": bool(sample_sufficient),
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "promotable": not failed,
        "checks": checks,
        "failed_checks": failed,
        "note": "Promotion readiness is a governance status, not a forecast probability.",
    }
