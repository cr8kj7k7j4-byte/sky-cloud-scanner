import json
from pathlib import Path

from src.market_intelligence import summarize_market
from src.feature_engine import build_features
from src.strategy_builder import build_breakout_plan, apply_plan
from src.ranking_engine import rank_candidates
from src.risk_engine import RiskPolicy, evaluate_candidate
from src.execution_engine import ExecutionCostPolicy
from src.monitor_engine import evaluate_monitor_state
from src.paper_trading import evaluate_paper_gate, build_paper_snapshot
from src.outcome_engine import evaluate_long_outcome
from src.trade_logger import TradeRecord, evaluate_trade_record


def _candles():
    return {
        "data": [
            {"high": 10.00, "low": 9.80, "close": 9.90, "volume": 100},
            {"high": 10.10, "low": 9.85, "close": 10.00, "volume": 110},
            {"high": 10.20, "low": 9.90, "close": 10.10, "volume": 120},
            {"high": 10.15, "low": 9.95, "close": 10.10, "volume": 125},
            {"high": 10.25, "low": 10.00, "close": 10.20, "volume": 150},
            {"high": 10.40, "low": 10.15, "close": 10.30, "volume": 200},
        ]
    }


def _execution_policy(enforce=True):
    return ExecutionCostPolicy(
        buy_commission_rate=0.000333,
        sell_commission_rate=0.000333,
        sell_tax_rate=0.0015,
        entry_slippage_bps=5,
        exit_slippage_bps=5,
        spread_bps=10,
        liquidity_penalty_bps=0,
        fill_probability=0.9,
        min_execution_rr=1.5,
        enforce_gate=enforce,
    )


def _base_candidate(last=10.21):
    return {
        "symbol": "TEST",
        "name": "Sky E2E Fixture",
        "exchange": "TWSE",
        "last": last,
        "fugle_close": last,
        "fugle_high": 10.40,
        "fugle_low": 9.80,
        "avg_price": 9.95,
        "change_pct": 2.1,
        "volume": 5000,
        "trade_value": 50_000_000,
        "quote_time": "2026-10-25T09:35:00+08:00",
        "quote_source": "E2E_FIXTURE",
        "grade": "A+",
        "flags": [],
    }


def _build_chain(last=10.21, daily_pnl=0.0, execution_policy=None):
    market = summarize_market([
        {"symbol": "A", "name": "A", "change_pct": 1.2, "trade_value": 50_000_000},
        {"symbol": "B", "name": "B", "change_pct": 0.8, "trade_value": 40_000_000},
        {"symbol": "C", "name": "C", "change_pct": 0.5, "trade_value": 30_000_000},
        {"symbol": "D", "name": "D", "change_pct": -0.2, "trade_value": 20_000_000},
        {"symbol": "E", "name": "E", "change_pct": 0.4, "trade_value": 10_000_000},
    ])
    assert market["status"] == "OK"

    c = _base_candidate(last)
    bars = _candles()
    features = build_features(
        c,
        candles=bars["data"],
        market_return_pct=market["median_change_pct"],
    ).to_dict()
    c["feature_envelope"] = {"features": features, "schema_version": "E2E-1"}

    plan = build_breakout_plan(c, bars)
    assert plan is not None
    c = apply_plan(c, plan)

    ranked = rank_candidates([c])
    assert len(ranked) == 1
    c = ranked[0]
    assert c["ranking_model"]["production_eligible"] is False

    portfolio = {
        "account_equity": 1_000_000,
        "daily_pnl": daily_pnl,
        "open_risk": 0,
        "concurrent_positions": 0,
        "correlated_open_risk": 0,
        "drawdown_pct": 0,
        "consecutive_losses": 0,
        "execution_policy": execution_policy,
    }
    c["risk"] = evaluate_candidate(c, portfolio, policy=RiskPolicy())
    c["monitor"] = evaluate_monitor_state(c).to_dict()
    return market, c


def test_happy_path_reaches_shadow_but_not_live_execution():
    market, c = _build_chain(last=10.25, execution_policy=_execution_policy(True))

    assert market["market_bias"] in {"BULLISH", "NEUTRAL", "BEARISH"}
    assert c["strategy_plan"]["production_eligible"] is False
    assert c["risk"]["status"] == "ALLOW"
    assert c["risk"]["portfolio_allowed"] is True
    assert c["risk"]["execution_status"] == "COMPLETE"
    assert c["risk"]["execution_adjusted_rr"] >= 1.5

    # TRIGGERED remains pending confirmation; never auto-buy.
    assert c["monitor"]["state"] == "TRIGGERED"
    assert c["monitor"]["action"] == "等待"

    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    snap = build_paper_snapshot(
        run_id="e2e-allow",
        observed_at="2026-10-25T09:35:00+08:00",
        item=c,
        gate=gate,
    )
    assert snap["action"] == "SHADOW_OBSERVE"
    assert snap["paper_gate"]["simulation_allowed"] is False
    assert snap["strategy"]["production_eligible"] is False


def test_daily_loss_limit_blocks_before_execution_action():
    _, c = _build_chain(
        daily_pnl=-15_000,
        execution_policy=_execution_policy(True),
    )
    assert c["risk"]["status"] == "BLOCK"
    assert c["risk"]["portfolio_allowed"] is False
    assert any("Daily Loss Limit" in x for x in c["risk"]["reasons"])
    assert c["monitor"]["state"] == "BLOCKED"
    assert c["monitor"]["action"] == "禁止交易"


def test_anti_chase_invalidates_even_without_risk_block():
    _, c = _build_chain(
        last=10.40,
        execution_policy=_execution_policy(True),
    )
    # Force risk to ALLOW so this case isolates the monitor anti-chase rule.
    c["risk"]["status"] = "ALLOW"
    c["risk"]["portfolio_allowed"] = True
    c["monitor"] = evaluate_monitor_state(c).to_dict()
    assert c["last"] > c["max_entry"]
    assert c["monitor"]["state"] == "INVALIDATED"
    assert c["monitor"]["action"] == "禁止交易"


def test_missing_execution_inputs_never_become_zero_cost_assumptions():
    _, c = _build_chain(
        execution_policy=ExecutionCostPolicy(enforce_gate=True),
    )
    assert c["risk"]["status"] == "BLOCK"
    assert c["risk"]["execution_status"] == "EXECUTION_INPUT_REQUIRED"
    assert "EXECUTION_INPUT_REQUIRED" in c["risk"]["reasons"]
    assert c["monitor"]["state"] == "BLOCKED"


def test_outcome_and_ledger_are_reproducible():
    out = evaluate_long_outcome(
        entry=10.21,
        stop=9.80,
        target=11.00,
        bars=[
            {"high": 10.50, "low": 10.10, "close": 10.40},
            {"high": 10.80, "low": 10.30, "close": 10.70},
            {"high": 11.05, "low": 10.60, "close": 11.00},
        ],
        exit_price=11.00,
        fee_rate=0.000333,
        tax_rate=0.0015,
        slippage_rate=0.0005,
    )
    assert out.status == "COMPLETE"
    assert out.hit_target is True
    assert out.r_multiple is not None

    record = TradeRecord(
        symbol="TEST",
        side="LONG",
        entry_time="2026-10-25T09:35:00+08:00",
        entry_price=10.21,
        exit_time="2026-10-25T10:05:00+08:00",
        exit_price=11.00,
        quantity=1000,
        initial_stop=9.80,
        fees=7.06,
        tax=16.50,
        slippage=10.61,
        max_price_during_trade=11.05,
        min_price_during_trade=10.10,
        setup="E2E_ACCEPTANCE",
        model_version="Sky-V2.1",
    )
    ledger = evaluate_trade_record(record)
    assert ledger["net_pnl"] < ledger["gross_pnl"]
    assert ledger["r_multiple"] is not None
    assert ledger["holding_minutes"] == 30.0
