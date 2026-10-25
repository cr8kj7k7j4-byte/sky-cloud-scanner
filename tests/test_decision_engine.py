from src.decision_engine import evaluate_decision


def _base():
    return {
        "symbol": "TEST",
        "classification_cap": "A",
        "strategy_plan": {"production_eligible": False},
        "risk": {"status": "ALLOW", "reasons": []},
        "monitor": {"state": "TRIGGERED", "action": "等待", "reason": "已觸發"},
        "evidence_ledger": {
            "items": [{"x": 1}],
            "decision_eligible": True,
            "stale_count": 0,
            "conflict": False,
        },
        "agent_orchestration": {"decision_status": "REVIEW_READY"},
        "flags": [],
    }


def test_triggered_is_wait_not_buy():
    d = evaluate_decision(_base()).to_dict()
    assert d["status"] == "WAIT"
    assert d["action"] == "等待"
    assert d["live_execution_allowed"] is False
    assert d["guardrails"]["triggered_is_not_buy"] is True


def test_risk_block_has_priority():
    c = _base()
    c["risk"] = {"status": "BLOCK", "reasons": ["Daily Loss Limit"]}
    d = evaluate_decision(c).to_dict()
    assert d["status"] == "BLOCK"
    assert d["action"] == "禁止交易"
    assert "Daily Loss Limit" in d["reasons"]


def test_evidence_conflict_requires_data_review():
    c = _base()
    c["evidence_ledger"] = {
        "items": [{"x": 1}],
        "decision_eligible": False,
        "stale_count": 0,
        "conflict": True,
    }
    d = evaluate_decision(c).to_dict()
    assert d["status"] == "DATA_REQUIRED"
    assert d["evidence_eligible"] is False


def test_ranking_never_controls_decision_contract():
    c = _base()
    c["ranking_model"] = {"score": 999, "production_eligible": True}
    d = evaluate_decision(c).to_dict()
    assert d["guardrails"]["ranking_input_used"] is False


def test_research_strategy_never_becomes_live_signal():
    d = evaluate_decision(_base()).to_dict()
    assert d["strategy_production_eligible"] is False
    assert d["live_execution_allowed"] is False
    assert any("research-only" in x for x in d["reasons"])
