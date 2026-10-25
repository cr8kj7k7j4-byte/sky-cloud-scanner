import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.model_registry import build_shadow_promotion_dashboard
from research.shadow_promotion_dashboard import load_shadow_records


def _records(n=50, days=10, symbols=5, regimes=("BULL", "NEUTRAL")):
    rows=[]
    for i in range(n):
        day=(i % days)+1
        rows.append({
            "observed_at": f"2026-10-{day:02d}T09:30:00+08:00",
            "symbol": f"S{i % symbols:02d}",
            "research_context": {"regime": regimes[i % len(regimes)]},
            "outcome": {"status": "COMPLETE", "r_multiple": 0.2},
        })
    return rows


def test_dashboard_reports_accumulation_gaps():
    dashboard = build_shadow_promotion_dashboard(_records())
    assert dashboard["stage"] == "ACCUMULATING"
    assert dashboard["sample_gaps"]["samples_remaining"] == 150
    assert dashboard["sample_gaps"]["trading_days_remaining"] == 10
    assert dashboard["summary"]["promotable_to_governance_review"] is False


def test_dashboard_sample_ready_but_not_promotion_ready():
    dashboard = build_shadow_promotion_dashboard(
        _records(n=200, days=20, symbols=10),
        promotion_evidence={
            "metrics": {
                "oos_expectancy_r": 0.1,
                "oos_pf": 1.2,
                "oos_max_drawdown_r": 4.0,
            },
            "validation": {
                "walk_forward_passed": True,
                "oos_passed": True,
                "cost_stress_passed": True,
                "leakage_check_passed": True,
                "survivorship_reviewed": True,
                "regime_stability_passed": True,
                "paper_trade_passed": False,
            },
        },
        max_drawdown_r=5.0,
    )
    assert dashboard["stage"] == "SAMPLE_READY"
    assert dashboard["sample_sufficiency"]["sufficient"] is True
    assert "promotion:paper_trade" in dashboard["blocking_items"]


def test_dashboard_governance_review_ready_only_after_all_gates():
    dashboard = build_shadow_promotion_dashboard(
        _records(n=200, days=20, symbols=10),
        promotion_evidence={
            "metrics": {
                "oos_expectancy_r": 0.1,
                "oos_pf": 1.2,
                "oos_max_drawdown_r": 4.0,
            },
            "validation": {
                "walk_forward_passed": True,
                "oos_passed": True,
                "cost_stress_passed": True,
                "leakage_check_passed": True,
                "survivorship_reviewed": True,
                "regime_stability_passed": True,
                "paper_trade_passed": True,
            },
        },
        max_drawdown_r=5.0,
    )
    assert dashboard["stage"] == "GOVERNANCE_REVIEW_READY"
    assert dashboard["promotion_scorecard"]["score"] == 100.0
    assert dashboard["promotion_scorecard"]["production_eligible"] is False


def test_runner_loads_multiple_paper_files():
    with TemporaryDirectory() as td:
        root=Path(td)
        p1=root/"run1"/"output"/"paper"
        p2=root/"run2"/"output"/"paper"
        p1.mkdir(parents=True)
        p2.mkdir(parents=True)
        (p1/"a.json").write_text(
            json.dumps({"records": _records(n=2, days=2, symbols=2)}),
            encoding="utf-8",
        )
        (p2/"b.json").write_text(
            json.dumps({"records": _records(n=3, days=3, symbols=3)}),
            encoding="utf-8",
        )
        (root/"unrelated.json").write_text(
            json.dumps({"records": _records(n=99)}),
            encoding="utf-8",
        )
        rows, files = load_shadow_records(root)
        assert len(rows) == 5
        assert len(files) == 2
