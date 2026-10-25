from src.outcome_engine import (
    evaluate_ranking_outcome,
    evaluate_shadow_long_path,
)
from research.shadow_outcome_backfill import (
    bars_after_observation,
    backfill_record,
)


def _candles():
    return {
        "data": [
            {
                "date": "2026-10-27T09:30:00+08:00",
                "high": 10.3, "low": 10.0, "close": 10.2,
            },
            {
                "date": "2026-10-27T09:35:00+08:00",
                "high": 10.4, "low": 10.1, "close": 10.3,
            },
            {
                "date": "2026-10-27T09:40:00+08:00",
                "high": 10.7, "low": 10.2, "close": 10.6,
            },
            {
                "date": "2026-10-27T09:45:00+08:00",
                "high": 10.8, "low": 10.5, "close": 10.7,
            },
        ]
    }


def test_bars_after_observation_are_strictly_future():
    bars = bars_after_observation(
        _candles(),
        "2026-10-27T09:35:00+08:00",
    )
    assert len(bars) == 2
    assert bars[0]["date"] == "2026-10-27T09:40:00+08:00"


def test_ranking_outcome_is_research_not_trade_fill():
    out = evaluate_ranking_outcome(
        reference_price=10.3,
        bars=bars_after_observation(
            _candles(),
            "2026-10-27T09:35:00+08:00",
        ),
    )
    assert out["status"] == "COMPLETE"
    assert out["outcome_type"] == "RANKING_SHADOW"
    assert out["research_only"] is True
    assert out["close_return_pct"] > 0
    assert "realized P&L" in out["note"]


def test_same_bar_stop_and_target_uses_conservative_stop_first():
    out = evaluate_shadow_long_path(
        entry=10.0,
        stop=9.8,
        target=10.4,
        bars=[{"high": 10.5, "low": 9.7, "close": 10.2}],
        fee_rate=0.000333,
        tax_rate=0.0015,
        entry_impact_rate=0.001,
        exit_impact_rate=0.001,
    )
    assert out["exit_reason"] == "STOP"
    assert out["exit"] == 9.8
    assert out["ambiguous_same_bar"] is True
    assert out["r_multiple"] < 0


def test_missing_execution_impact_never_becomes_zero_cost():
    out = evaluate_shadow_long_path(
        entry=10.0,
        stop=9.8,
        target=10.4,
        bars=[{"high": 10.5, "low": 9.9, "close": 10.4}],
        fee_rate=0.000333,
        tax_rate=0.0015,
        entry_impact_rate=None,
        exit_impact_rate=None,
    )
    assert out["status"] == "COST_INPUT_REQUIRED"
    assert out["gross_r_multiple"] is not None
    assert out["r_multiple"] is None


def test_backfill_keeps_nontriggered_record_as_ranking_only():
    record = {
        "run_id": "r1",
        "observed_at": "2026-10-27T09:35:00+08:00",
        "symbol": "TEST",
        "market": {"last": 10.3},
        "strategy": {"trigger": 10.3, "stop": 10.0, "target": 10.9},
        "risk": {"status": "ALLOW"},
        "monitor": {"state": "NEAR_TRIGGER"},
    }
    out = backfill_record(
        record,
        _candles(),
        {
            "profile_id": "TEST",
            "fee_rate": 0.000333,
            "tax_rate": 0.0015,
            "entry_impact_rate": 0.001,
            "exit_impact_rate": 0.001,
        },
    )
    assert out["outcome"]["status"] == "COMPLETE"
    assert out["outcome"]["ranking"]["status"] == "COMPLETE"
    assert (
        out["outcome"]["strategy_counterfactual"]["status"]
        == "NOT_ELIGIBLE"
    )


def test_backfill_triggered_record_can_create_counterfactual_strategy_outcome():
    record = {
        "run_id": "r2",
        "observed_at": "2026-10-27T09:35:00+08:00",
        "symbol": "TEST",
        "market": {"last": 10.3},
        "strategy": {"trigger": 10.3, "stop": 10.0, "target": 10.7},
        "risk": {"status": "ALLOW"},
        "monitor": {"state": "TRIGGERED"},
    }
    out = backfill_record(
        record,
        _candles(),
        {
            "profile_id": "TEST",
            "fee_rate": 0.000333,
            "tax_rate": 0.0015,
            "entry_impact_rate": 0.001,
            "exit_impact_rate": 0.001,
        },
    )
    strategy = out["outcome"]["strategy_counterfactual"]
    assert strategy["outcome_type"] == "COUNTERFACTUAL_SHADOW"
    assert strategy["research_only"] is True
    assert strategy["status"] == "COMPLETE"
