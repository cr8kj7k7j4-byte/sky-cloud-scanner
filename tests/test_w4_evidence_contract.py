from src.model_registry import build_shadow_promotion_dashboard



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
