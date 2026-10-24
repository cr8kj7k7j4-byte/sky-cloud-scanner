import pytest

from src.execution_engine import (
    ExecutionCostPolicy,
    evaluate_execution_rr,
    execution_gate,
)


def test_gross_rr_is_separate_from_cost_adjusted_rr():
    p = ExecutionCostPolicy()
    out = evaluate_execution_rr(entry=50, stop=48.5, target=53, policy=p)
    assert out["gross_rr"] == 2.0
    assert out["fee_tax_adjusted_rr"] is None
    assert out["execution_adjusted_rr"] is None
    assert out["status"] == "EXECUTION_INPUT_REQUIRED"
    assert "sell_tax_rate" in out["missing_inputs"]


def test_zero_cost_explicit_assumptions_preserve_gross_rr():
    p = ExecutionCostPolicy(
        buy_commission_rate=0,
        sell_commission_rate=0,
        sell_tax_rate=0,
        entry_slippage_bps=0,
        exit_slippage_bps=0,
        spread_bps=0,
        liquidity_penalty_bps=0,
        fill_probability=1,
    )
    out = evaluate_execution_rr(entry=50, stop=48.5, target=53, policy=p)
    assert out["status"] == "COMPLETE"
    assert out["gross_rr"] == 2.0
    assert out["fee_tax_adjusted_rr"] == 2.0
    assert out["execution_adjusted_rr"] == 2.0
    assert out["cost_drag_rr"] == 0.0


def test_costs_reduce_rr():
    p = ExecutionCostPolicy(
        buy_commission_rate=0.001,
        sell_commission_rate=0.001,
        sell_tax_rate=0.003,
        entry_slippage_bps=5,
        exit_slippage_bps=5,
        spread_bps=10,
        liquidity_penalty_bps=2,
        fill_probability=0.9,
    )
    out = evaluate_execution_rr(entry=50, stop=48.5, target=53, policy=p)
    assert out["fee_tax_adjusted_rr"] < out["gross_rr"]
    assert out["execution_adjusted_rr"] < out["fee_tax_adjusted_rr"]
    assert out["fill_adjusted_expected_rr"] < out["execution_adjusted_rr"]
    assert out["cost_drag_rr"] > 0


def test_execution_gate_never_assumes_missing_costs_are_zero():
    p = ExecutionCostPolicy(enforce_gate=True)
    out = evaluate_execution_rr(entry=50, stop=48.5, target=53, policy=p)
    allowed, reason = execution_gate(out)
    assert allowed is False
    assert reason == "EXECUTION_INPUT_REQUIRED"


def test_gate_can_block_after_complete_cost_model():
    p = ExecutionCostPolicy(
        buy_commission_rate=0.001,
        sell_commission_rate=0.001,
        sell_tax_rate=0.003,
        entry_slippage_bps=10,
        exit_slippage_bps=10,
        spread_bps=20,
        liquidity_penalty_bps=5,
        fill_probability=0.8,
        min_execution_rr=1.95,
        enforce_gate=True,
    )
    out = evaluate_execution_rr(entry=50, stop=48.5, target=53, policy=p)
    allowed, reason = execution_gate(out)
    assert out["status"] == "COMPLETE"
    assert allowed is False
    assert reason == "EXECUTION_RR_BELOW_MINIMUM"


def test_invalid_long_geometry_is_rejected():
    with pytest.raises(ValueError):
        evaluate_execution_rr(entry=50, stop=51, target=53)
