import pytest

from research.frozen_v14_evidence_replay_adapter import (
    CANONICAL_RULE_COLUMNS,
    assert_w2_rule_efficacy_allowed,
    build_evidence_preserving_replay_row,
)


def _blocked_registry():
    return {
        "rules": [
            {"rule": rule, "status": "UNRESOLVED", "reason": "missing"}
            for rule in CANONICAL_RULE_COLUMNS
        ]
    }


def test_unresolved_rules_are_never_invented():
    observed = {
        "symbol": "2330",
        "market_gate": True,
        "phase_gate": True,
        "price": 100.0,
    }
    row = build_evidence_preserving_replay_row(
        observed, source_registry=_blocked_registry()
    )
    assert row["price"] == 100.0
    assert row["market_gate"] is None
    assert row["phase_gate"] is None
    assert row["frozen_v14_replay_status"] == "FROZEN_ALPHA_INPUT_REQUIRED"
    assert row["w2_rule_efficacy_allowed"] is False
    assert set(row["frozen_v14_unresolved_rules"]) == set(CANONICAL_RULE_COLUMNS)


def test_allowed_provider_can_preserve_existing_historical_boolean():
    registry = _blocked_registry()
    registry["rules"][0] = {
        "rule": "market_gate",
        "status": "HISTORICAL_SNAPSHOT",
        "reason": "retained snapshot",
    }
    observed = {"market_gate": False}
    row = build_evidence_preserving_replay_row(
        observed, source_registry=registry
    )
    assert row["market_gate"] is False
    assert "market_gate" not in row["frozen_v14_unresolved_rules"]


def test_allowed_provider_without_row_value_still_blocks():
    registry = _blocked_registry()
    registry["rules"][0] = {
        "rule": "market_gate",
        "status": "FROZEN_CANONICAL_IMPLEMENTATION",
    }
    row = build_evidence_preserving_replay_row({}, source_registry=registry)
    assert row["market_gate"] is None
    assert "market_gate" in row["frozen_v14_unresolved_rules"]


def test_w2_guard_raises_when_frozen_alpha_missing():
    row = build_evidence_preserving_replay_row(
        {}, source_registry=_blocked_registry()
    )
    with pytest.raises(RuntimeError, match="missing frozen v1.4 providers"):
        assert_w2_rule_efficacy_allowed(row)
