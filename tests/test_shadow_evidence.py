from src.shadow_evidence import (
    evaluate_shadow_pipeline_readiness,
    evaluate_portfolio_cost_capacity_evidence,
)


def test_pipeline_waiting_is_not_failure_before_first_eligible_scan():
    out = evaluate_shadow_pipeline_readiness(
        ledger_start="2026-10-24T23:28:08Z",
        eligible_successful_scan_runs=0,
        paper_files=0,
        records_loaded=0,
    )
    assert out["status"] == "WAITING_FOR_FIRST_ELIGIBLE_SCAN"
    assert out["healthy"] is True
    assert out["collection_started"] is False


def test_pipeline_fails_closed_when_scan_exists_but_artifact_missing():
    out = evaluate_shadow_pipeline_readiness(
        ledger_start="2026-10-24T23:28:08Z",
        eligible_successful_scan_runs=1,
        paper_files=0,
        records_loaded=0,
    )
    assert out["status"] == "PIPELINE_ARTIFACT_MISSING"
    assert out["healthy"] is False


def test_pipeline_fails_closed_when_artifact_has_no_records():
    out = evaluate_shadow_pipeline_readiness(
        ledger_start="2026-10-24T23:28:08Z",
        eligible_successful_scan_runs=2,
        paper_files=2,
        records_loaded=0,
    )
    assert out["status"] == "PIPELINE_RECORDS_MISSING"
    assert out["healthy"] is False


def _complete_record(symbol="1111", r=0.5, shares=1000, trade_value=5_000_000):
    return {
        "symbol": symbol,
        "market": {"last": 50.0, "trade_value": trade_value},
        "strategy": {"trigger": 50.0},
        "risk": {"recommended_shares": shares},
        "outcome": {
            "strategy_counterfactual": {
                "status": "COMPLETE",
                "r_multiple": r,
            }
        },
    }


def test_portfolio_contract_is_not_evaluable_without_complete_outcomes():
    out = evaluate_portfolio_cost_capacity_evidence([])
    assert out["status"] == "NOT_EVALUABLE"
    assert out["production_eligible"] is False


def test_portfolio_contract_requires_capacity_assumption():
    rows = [
        _complete_record("1111", 0.5),
        _complete_record("2222", -0.2),
        _complete_record("3333", 0.4),
        _complete_record("4444", 0.1),
        _complete_record("5555", -0.1),
    ]
    out = evaluate_portfolio_cost_capacity_evidence(
        rows,
        max_symbol_share=0.20,
    )
    assert out["status"] == "CAPACITY_INPUT_REQUIRED"
    assert out["checks"]["capacity"] is None
    assert out["observed"]["complete_strategy_outcomes"] == 5
    assert out["observed"]["expectancy_r"] > 0


def test_portfolio_contract_can_evaluate_capacity_when_explicit():
    rows = [
        _complete_record("1111", 0.5, shares=1000, trade_value=10_000_000),
        _complete_record("2222", -0.2, shares=1000, trade_value=10_000_000),
        _complete_record("3333", 0.4, shares=1000, trade_value=10_000_000),
        _complete_record("4444", 0.1, shares=1000, trade_value=10_000_000),
        _complete_record("5555", -0.1, shares=1000, trade_value=10_000_000),
    ]
    out = evaluate_portfolio_cost_capacity_evidence(
        rows,
        max_symbol_share=0.20,
        max_participation_rate=0.01,
    )
    assert out["checks"]["capacity"] is True
    assert out["status"] == "EVIDENCE_READY"
    assert out["production_eligible"] is False
