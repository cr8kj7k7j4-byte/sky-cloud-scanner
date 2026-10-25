import tempfile
from pathlib import Path

from src.validation import (
    cost_stress_report,
    leakage_audit,
    aggregate_by_regime,
    ablation_delta,
)
from src.model_registry import (
    RuleRecord,
    register_rule,
    build_champion_config,
    set_champion_configuration,
    rollback_champion,
    registry_snapshot,
    promotion_readiness,
)
from src.readiness import default_sky100_checks, engineering_readiness


def test_validation_research_contracts():
    stress = cost_stress_report([2.0, 1.5, -0.2])
    assert len(stress["scenarios"]) == 3
    assert "passed" in stress

    leak = leakage_audit(
        ["momentum_5", "volume_ratio"],
        ["target_return"],
        {"timestamp_order_ok": True, "survivorship_reviewed": True},
    )
    assert leak["passed"] is True

    bad = leakage_audit(
        ["future_return", "mfe"],
        ["target_return"],
        {"timestamp_order_ok": True, "survivorship_reviewed": True},
    )
    assert bad["passed"] is False

    regimes = aggregate_by_regime([
        {"regime": "BULL", "net_r": 1.0},
        {"regime": "BULL", "net_r": -0.5},
        {"regime": "BEAR", "net_r": -1.0},
    ])
    assert regimes["BULL"]["n"] == 2

    delta = ablation_delta(
        {"expectancy_r": 0.2, "profit_factor": 1.4, "max_drawdown_r": -5},
        {"expectancy_r": 0.1, "profit_factor": 1.2, "max_drawdown_r": -7},
    )
    assert delta["expectancy_r"] > 0
    assert delta["max_drawdown_r"] > 0


def _rule(rule_id):
    return RuleRecord(
        rule_id=rule_id,
        version="1.0",
        status="VALIDATED",
        production_enabled=True,
        owner_module="test",
        rationale="test",
        evidence={},
        validation={
            "walk_forward_passed": True,
            "oos_passed": True,
            "cost_stress_passed": True,
            "leakage_check_passed": True,
            "paper_trade_passed": True,
        },
        rollback={"available": True},
        created_at="2026-10-25T00:00:00+00:00",
    )


def test_rule_registry_folds_into_existing_p0g():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "registry.json"
        ids = [
            "market_gate","sector_rs_gate","anti_chase_gate",
            "phase_gate","setup_gate","trigger_gate","rr_gate",
        ]
        for rid in ids:
            register_rule(path, _rule(rid))

        config = build_champion_config(
            config_id="sky-core",
            version="1.0",
            rule_versions={rid:"1.0" for rid in ids},
            model_version="research-only",
            feature_schema_version="1.0",
        )
        payload = set_champion_configuration(path, config)
        assert payload["champion_configuration"]["config_id"] == "sky-core"

        prior = {"config_id":"prior","version":"0.9","rules":{}}
        rolled = rollback_champion(path, prior)
        assert rolled["champion_configuration"]["config_id"] == "prior"

        snap = registry_snapshot(path)
        assert "rules" in snap


def test_readiness_requires_new_canonical_modules():
    checks = default_sky100_checks(
        official_data_chain=True,
        feature_contract=True,
        knowledge_engine=False,
        decision_engine=True,
        ranking_engine=False,
        risk_engine=True,
        position_manager=False,
        trade_logging=True,
        walk_forward=True,
        oos=True,
        cost_stress=True,
        leakage_check=True,
        paper_trade=True,
        monitoring=True,
    )
    result = engineering_readiness(checks)
    assert result["production_ready"] is False
    assert "P0-K Knowledge/Evidence" in result["blocking_components"]
    assert "P0-O Ranking Engine" in result["blocking_components"]
    assert "PMS Position Manager" in result["blocking_components"]


def test_promotion_readiness_never_uses_accuracy_only():
    gate = promotion_readiness(
        walk_forward=True,
        oos=True,
        cost_stress=True,
        leakage_check=True,
        survivorship_review=True,
        regime_stability=True,
        paper_trade=False,
        sample_sufficient=True,
    )
    assert gate["promotable"] is False
    assert "paper_trade" in gate["failed_checks"]
