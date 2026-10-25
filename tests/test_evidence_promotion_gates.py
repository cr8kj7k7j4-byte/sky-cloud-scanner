from src.model_registry import (
    evaluate_shadow_sample_sufficiency,
    build_promotion_scorecard,
)
from src.paper_trading import evaluate_paper_gate, build_paper_snapshot


def _shadow_records(n=200, days=20, symbols=10, regimes=("BULL", "NEUTRAL")):
    rows = []
    for i in range(n):
        day = (i % days) + 1
        symbol = f"S{i % symbols:02d}"
        regime = regimes[i % len(regimes)]
        rows.append({
            "observed_at": f"2026-10-{day:02d}T09:30:00+08:00",
            "symbol": symbol,
            "research_context": {"regime": regime, "setup": "TEST"},
            "outcome": {"status": "COMPLETE", "r_multiple": 0.2},
        })
    return rows


def test_shadow_sample_sufficiency_blocks_small_sample():
    result = evaluate_shadow_sample_sufficiency(
        _shadow_records(n=50, days=10, symbols=10)
    )
    assert result["sufficient"] is False
    assert "sample_count" in result["failed_checks"]
    assert "trading_days" in result["failed_checks"]


def test_shadow_sample_sufficiency_blocks_symbol_concentration():
    rows = _shadow_records(n=200, days=20, symbols=1)
    result = evaluate_shadow_sample_sufficiency(rows)
    assert result["sufficient"] is False
    assert "symbol_concentration" in result["failed_checks"]


def test_shadow_sample_sufficiency_passes_diverse_complete_sample():
    result = evaluate_shadow_sample_sufficiency(
        _shadow_records(n=200, days=20, symbols=10)
    )
    assert result["sufficient"] is True
    assert result["observed"]["regime_count"] == 2
    assert result["observed"]["outcome_complete_ratio"] == 1.0
    assert result["observed"]["top_symbol_share"] <= 0.20


def test_promotion_scorecard_blocks_missing_paper_gate():
    evidence = {
        "sample_sufficient": True,
        "metrics": {
            "oos_expectancy_r": 0.10,
            "oos_pf": 1.25,
            "oos_max_drawdown_r": 4.0,
        },
        "validation": {
            "sample_sufficient": True,
            "walk_forward_passed": True,
            "oos_passed": True,
            "cost_stress_passed": True,
            "leakage_check_passed": True,
            "survivorship_reviewed": True,
            "regime_stability_passed": True,
            "paper_trade_passed": False,
        },
    }
    card = build_promotion_scorecard(
        evidence,
        artifact_type="RANKING",
        max_drawdown_r=5.0,
    )
    assert card["promotable_to_governance_review"] is False
    assert "paper_trade" in card["failed_checks"]
    assert card["production_eligible"] is False


def test_promotion_scorecard_full_pass_is_review_only():
    evidence = {
        "sample_sufficient": True,
        "metrics": {
            "oos_expectancy_r": 0.10,
            "oos_pf": 1.25,
            "oos_max_drawdown_r": 4.0,
        },
        "validation": {
            "sample_sufficient": True,
            "walk_forward_passed": True,
            "oos_passed": True,
            "cost_stress_passed": True,
            "leakage_check_passed": True,
            "survivorship_reviewed": True,
            "regime_stability_passed": True,
            "paper_trade_passed": True,
        },
    }
    card = build_promotion_scorecard(
        evidence,
        artifact_type="MODEL",
        max_drawdown_r=5.0,
    )
    assert card["score"] == 100.0
    assert card["promotable_to_governance_review"] is True
    assert card["production_eligible"] is False
    assert "不代表勝率" in card["meaning"]


def test_shadow_snapshot_contains_research_context():
    item = {
        "symbol": "TEST",
        "name": "Sky",
        "ml": {"regime": {"label": "BULL"}},
        "strategy_plan": {"setup": "P3", "production_eligible": False},
        "outcome": {"status": "COMPLETE", "r_multiple": 0.5},
        "decision": {"status": "WAIT"},
    }
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    snap = build_paper_snapshot(
        run_id="r1",
        observed_at="2026-10-25T09:30:00+08:00",
        item=item,
        gate=gate,
    )
    assert snap["research_context"]["regime"] == "BULL"
    assert snap["research_context"]["setup"] == "P3"
    assert snap["outcome"]["status"] == "COMPLETE"
