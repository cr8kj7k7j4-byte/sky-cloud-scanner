from src.decision_engine import evaluate_decision
from src.paper_trading import evaluate_paper_gate, build_paper_snapshot
from src.trade_logger import build_trade_decision_record


def _candidate():
    c = {
        "symbol": "TEST",
        "name": "Sky Test",
        "exchange": "TWSE",
        "last": 10.25,
        "classification_cap": "A",
        "strategy_plan": {
            "setup": "5分K平台突破候選",
            "trigger": 10.25,
            "max_entry": 10.35,
            "stop": 9.95,
            "target": 10.85,
            "rr": 2.0,
            "production_eligible": False,
        },
        "risk": {
            "status": "ALLOW",
            "portfolio_allowed": True,
            "reasons": [],
        },
        "monitor": {
            "state": "TRIGGERED",
            "action": "等待",
            "reason": "價格已達觸發價，仍需確認",
        },
        "evidence_ledger": {
            "items": [{"category": "market_price"}],
            "decision_eligible": True,
            "stale_count": 0,
            "conflict": False,
        },
        "agent_orchestration": {"decision_status": "REVIEW_READY"},
        "flags": [],
    }
    c["decision"] = evaluate_decision(c).to_dict()
    return c


def test_decision_is_consistent_across_runtime_ledgers():
    c = _candidate()
    assert c["decision"]["status"] == "WAIT"

    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    snap = build_paper_snapshot(
        run_id="r1",
        observed_at="2026-10-25T09:30:00+08:00",
        item=c,
        gate=gate,
    )
    assert snap["decision"]["status"] == "WAIT"
    assert snap["action"] == "SHADOW_OBSERVE"

    rec = build_trade_decision_record(
        item=c,
        run_id="r1",
        observed_at="2026-10-25T09:30:00+08:00",
    )
    assert rec.decision == "WAIT"


def test_canonical_decision_overrides_legacy_risk_status_in_ledger():
    c = _candidate()
    assert c["risk"]["status"] == "ALLOW"
    assert c["decision"]["status"] == "WAIT"
    rec = build_trade_decision_record(
        item=c,
        run_id="r2",
        observed_at="2026-10-25T09:30:00+08:00",
    )
    assert rec.decision == "WAIT"
