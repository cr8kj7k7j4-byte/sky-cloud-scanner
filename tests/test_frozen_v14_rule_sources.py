from research.audit_frozen_v14_rule_sources import audit_registry

def test_unresolved_rules_block_deterministic_replay():
    out=audit_registry({
        "strategy_id":"v1.4",
        "rules":[
            {"rule":"market_gate","status":"HISTORICAL_SNAPSHOT"},
            {"rule":"phase_gate","status":"UNRESOLVED","reason":"missing"},
        ],
    })
    assert out["status"]=="BLOCKED"
    assert out["deterministic_historical_decision_replay_allowed"] is False
    assert out["coverage"]==0.5

def test_all_frozen_sources_allow_replay_provenance_gate():
    out=audit_registry({
        "strategy_id":"v1.4",
        "rules":[
            {"rule":"market_gate","status":"HISTORICAL_SNAPSHOT"},
            {"rule":"phase_gate","status":"FROZEN_CANONICAL_IMPLEMENTATION"},
        ],
    })
    assert out["status"]=="PASS"
    assert out["deterministic_historical_decision_replay_allowed"] is True
