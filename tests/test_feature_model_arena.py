import tempfile
from pathlib import Path

from src.feature_store import (
    FEATURE_SCHEMA_VERSION,
    build_feature_envelope,
    append_feature_snapshot,
)
from src.model_arena import ArenaResult, rank_models, choose_champion


def main():
    features = {
        "momentum_1": 0.5,
        "momentum_5": 2.0,
        "volume_ratio": 1.8,
        "vwap_distance_pct": 0.6,
        "intraday_range_pct": 3.2,
        "volatility_5": 1.1,
        "relative_strength": 1.4,
    }
    env = build_feature_envelope("2409", features, source="test")
    assert env.schema_version == FEATURE_SCHEMA_VERSION
    assert env.quality["valid_schema"] is True
    assert env.quality["completeness"] == 1.0

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "features.jsonl"
        out = append_feature_snapshot(p, env)
        assert out["symbol"] == "2409"
        assert p.exists()

    base_validation = {
        "walk_forward_passed": True,
        "oos_passed": True,
        "cost_stress_passed": True,
        "leakage_check_passed": True,
        "paper_trade_passed": True,
    }
    rule = ArenaResult(
        name="Sky Rule Engine",
        family="RULE",
        production_eligible=True,
        metrics={
            "expectancy_r": 0.08,
            "profit_factor": 1.15,
            "max_drawdown_r": 4.0,
            "stability_score": 0.8,
        },
        validation=base_validation,
    )
    xgb = ArenaResult(
        name="XGBoost",
        family="TREE_BOOSTING",
        production_eligible=True,
        metrics={
            "expectancy_r": 0.12,
            "profit_factor": 1.25,
            "max_drawdown_r": 3.5,
            "stability_score": 0.9,
        },
        validation=base_validation,
    )
    rf_research = ArenaResult(
        name="Random Forest",
        family="TREE",
        production_eligible=False,
        metrics={
            "expectancy_r": 0.20,
            "profit_factor": 1.40,
            "max_drawdown_r": 3.0,
            "stability_score": 1.0,
        },
        validation={**base_validation, "paper_trade_passed": False},
    )

    ranked = rank_models([rule, rf_research, xgb])
    assert ranked[0]["name"] == "XGBoost"
    assert choose_champion([rule, rf_research, xgb])["name"] == "XGBoost"

    print("PASS Feature Store + Model Arena tests")


if __name__ == "__main__":
    main()
