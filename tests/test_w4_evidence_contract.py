from src.paper_trading import build_paper_snapshot, evaluate_paper_gate
from src.model_registry import build_shadow_promotion_dashboard


def test_w4_paper_snapshot_persists_required_evidence_fields():
    item = {
        "symbol": "2409",
        "name": "TEST",
        "strategy_id": "sky-day-v1.4",
        "strategy_version": "1.4",
        "sector": "DISPLAY",
        "phase": "P3",
        "ranking_position": 2,
        "rank_score": 88.5,
        "ml": {"regime": {"label": "NEUTRAL"}},
        "strategy_plan": {
            "setup": "PULLBACK",
            "trigger": 37.5,
            "entry": 37.5,
            "max_entry": 37.8,
            "stop": 36.9,
            "target": 38.7,
            "target_2": 39.3,
        },
        "risk": {"status": "ALLOW"},
        "data_quality": {"status": "PASS"},
        "missing_data": [],
    }
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    row = build_paper_snapshot(
        run_id="r1",
        observed_at="2026-10-26T09:15:00+08:00",
        item=item,
        gate=gate,
    )

    required = {
        "strategy_id", "strategy_version", "symbol", "observation_timestamp",
        "market_regime", "sector", "ranking_position", "rank_score", "phase",
        "setup", "trigger", "trigger_price", "assumed_entry",
        "max_acceptable_price", "stop", "target_1", "target_2",
        "p0_r_decision", "risk_per_share", "data_quality", "missing_data",
        "outcome_completeness",
    }
    assert required.issubset(row)
    assert row["risk_per_share"] == 0.6
    assert row["target_2"] == 39.3
    assert row["p0_r_decision"] == "ALLOW"


def test_w4_sample_gate_uses_waiting_for_future_sample():
    rows = [{
        "observed_at": "2026-10-26T09:15:00+08:00",
        "symbol": "2409",
        "research_context": {"regime": "NEUTRAL"},
        "outcome": {},
    }]
    out = build_shadow_promotion_dashboard(rows)
    assert out["stage"] == "WAITING_FOR_FUTURE_SAMPLE"
    assert out["summary"]["promotable_to_governance_review"] is False
