import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rule_registry import (
    RuleRecord,
    load_registry,
    register_rule,
    set_champion_configuration,
    rollback_champion,
)
from src.champion_config import build_champion_config, promotion_readiness


def validated_rule(rule_id):
    return RuleRecord(
        rule_id=rule_id,
        version="1.0.0",
        status="VALIDATED",
        production_enabled=True,
        owner_module="P0-G",
        rationale="test",
        evidence={"phase5": True, "phase6": True, "phase7": True},
        validation={
            "walk_forward_passed": True,
            "oos_passed": True,
            "cost_stress_passed": True,
            "leakage_check_passed": True,
            "paper_trade_passed": True,
        },
        rollback={"enabled": True},
        created_at="2026-10-25T00:00:00+00:00",
    )


def main():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "rules.json"

        ids = [
            "market_gate",
            "sector_rs_gate",
            "anti_chase_gate",
            "phase_gate",
            "setup_gate",
            "trigger_gate",
            "rr_gate",
        ]
        for rule_id in ids:
            register_rule(path, validated_rule(rule_id))

        snap = load_registry(path)
        assert len(snap["rules"]) == 7

        config = build_champion_config(
            config_id="sky-core",
            version="2.1.0",
            rule_versions={x: "1.0.0" for x in ids},
            model_version="rule-engine-1.0",
            feature_schema_version="1.0.0",
            rollback_to={"config_id": "sky-core", "version": "2.0.0"},
        )
        updated = set_champion_configuration(path, config)
        assert updated["champion_configuration"]["version"] == "2.1.0"

        old = {
            "config_id": "sky-core",
            "version": "2.0.0",
            "rules": {x: "0.9.0" for x in ids},
        }
        rolled = rollback_champion(path, old)
        assert rolled["champion_configuration"]["version"] == "2.0.0"

        readiness = promotion_readiness(
            walk_forward=True,
            oos=True,
            cost_stress=True,
            leakage_check=True,
            survivorship_review=True,
            regime_stability=True,
            paper_trade=False,
            sample_sufficient=True,
        )
        assert readiness["promotable"] is False
        assert "paper_trade" in readiness["failed_checks"]

    print("PASS P0-G Rule Registry + Champion Configuration tests")


if __name__ == "__main__":
    main()
