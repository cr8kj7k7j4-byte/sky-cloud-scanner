import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

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


def test_dashboard_reports_future_sample_waiting_gaps():
    dashboard = build_shadow_promotion_dashboard(_records())
    assert dashboard["stage"] == "WAITING_FOR_FUTURE_SAMPLE"
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
        rows1 = _records(n=2, days=2, symbols=2)
        rows2 = _records(n=3, days=3, symbols=3)
        for row in rows1:
            row["run_id"] = "run1"
        for row in rows2:
            row["run_id"] = "run2"

        (p1/"a.json").write_text(
            json.dumps({"records": rows1}),
            encoding="utf-8",
        )
        (p2/"b.json").write_text(
            json.dumps({"records": rows2}),
            encoding="utf-8",
        )
        (root/"unrelated.json").write_text(
            json.dumps({"records": _records(n=99)}),
            encoding="utf-8",
        )
        rows, files = load_shadow_records(root)
        assert len(rows) == 5
        assert len(files) == 2



def test_loader_prefers_enriched_outcome_record():
    with TemporaryDirectory() as td:
        root = Path(td)
        raw_dir = root / "scan" / "output" / "paper"
        out_dir = root / "outcome" / "output" / "paper"
        raw_dir.mkdir(parents=True)
        out_dir.mkdir(parents=True)

        base = {
            "run_id": "r1",
            "observed_at": "2026-10-27T09:35:00+08:00",
            "symbol": "TEST",
            "research_context": {"regime": "BULL"},
            "outcome": {},
        }
        enriched = {
            **base,
            "outcome": {
                "status": "COMPLETE",
                "ranking": {"status": "COMPLETE"},
            },
        }
        (raw_dir / "raw.json").write_text(
            json.dumps({"records": [base]}), encoding="utf-8"
        )
        (out_dir / "2026-10-27-outcomes.json").write_text(
            json.dumps({"records": [enriched]}), encoding="utf-8"
        )

        rows, _ = load_shadow_records(root)
        assert len(rows) == 1
        assert rows[0]["outcome"]["ranking"]["status"] == "COMPLETE"


def test_unknown_regimes_do_not_pass_w4_coverage():
    rows = _records(n=200, days=20, symbols=10, regimes=("UNKNOWN_LOW", "UNKNOWN_MEDIUM"))
    out = build_shadow_promotion_dashboard(rows)
    assert out["sample_sufficiency"]["checks"]["sample_count"] is True
    assert out["sample_sufficiency"]["checks"]["trading_days"] is True
    assert out["sample_sufficiency"]["checks"]["regime_coverage"] is False
    assert out["sample_sufficiency"]["observed"]["regime_count"] == 0
    assert out["stage"] == "WAITING_FOR_FUTURE_SAMPLE"


def test_verified_bull_neutral_bear_regimes_are_counted():
    rows = _records(n=200, days=20, symbols=10, regimes=("BULL", "NEUTRAL", "BEAR"))
    out = build_shadow_promotion_dashboard(rows)
    assert out["sample_sufficiency"]["checks"]["regime_coverage"] is True
    assert out["sample_sufficiency"]["observed"]["regime_count"] == 3


def test_loader_rejects_two_p0l_ids_for_same_observation():
    with TemporaryDirectory() as td:
        root = Path(td)
        p = root / "a" / "paper"
        q = root / "b" / "paper"
        p.mkdir(parents=True)
        q.mkdir(parents=True)
        row = {"run_id": "r1", "symbol": "2330",
               "observed_at": "2026-11-06T09:35:00+08:00",
               "record_id": "canonical-A", "outcome": {}}
        (p / "raw.json").write_text(
            json.dumps({"records": [row]}), encoding="utf-8")
        (q / "outcome.json").write_text(
            json.dumps({"records": [{**row, "record_id": "canonical-B",
                                    "outcome": {"status": "COMPLETE"}}]}),
            encoding="utf-8")
        with pytest.raises(ValueError, match="CONFLICTING_P0L_RECORD_ID"):
            load_shadow_records(root)


def test_mobile_report_displays_missing_p0l_ids():
    from research.shadow_promotion_dashboard import build_w4_report_sections
    dashboard = {
        "decision_outcome_reconciliation": {
            "status": "HOLD_PENDING_APPROVED_DECISION_SOURCE",
            "unique_record_ids": 0,
            "duplicate_rows": 0,
            "conflicting_duplicates": 0,
            "reasons": {"MISSING_RECORD_ID": 100},
        }
    }
    report = build_w4_report_sections(dashboard)
    section = report["Decision / Outcome Reconciliation"]
    assert section["missing_record_ids"] == 100
    assert section["eligible_strategy_trades"] == 0
