from src.agent_orchestrator import orchestrate
from src.knowledge_engine import Evidence, build_evidence_ledger


def test_p0_r_cannot_be_bypassed():
    candidate = {
        "symbol": "2330",
        "change_pct": 2.0,
        "features": {"momentum_5": 2.0, "volume_ratio": 1.5, "vwap_distance_pct": 0.5},
        "risk": {"status": "BLOCK", "reasons": ["Daily Loss Limit"]},
    }
    ledger = build_evidence_ledger([
        Evidence("2330", "market_price", "價格 100", "exchange", "TWSE")
    ])
    result = orchestrate(candidate, ledger)
    assert result["decision_status"] == "BLOCK"
    assert result["guardrails"]["must_pass_p0_r"] is True


def test_clean_evidence_and_allow_risk_is_review_ready():
    candidate = {
        "symbol": "2330",
        "change_pct": 1.0,
        "features": {"momentum_5": 1.0, "volume_ratio": 1.3, "vwap_distance_pct": 0.4},
        "risk": {"status": "ALLOW", "reasons": []},
    }
    ledger = build_evidence_ledger([
        Evidence("2330", "market_price", "價格 100", "exchange", "TWSE")
    ])
    result = orchestrate(candidate, ledger)
    assert result["decision_status"] == "REVIEW_READY"
    assert result["guardrails"]["single_agent_can_trade"] is False
