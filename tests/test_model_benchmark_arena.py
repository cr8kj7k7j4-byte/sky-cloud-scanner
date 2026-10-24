import numpy as np

from research.model_benchmark_arena import (
    BenchmarkConfig,
    SkyRuleBaseline,
    evaluate_predictions,
)
from src.benchmark_gate import benchmark_gate


def main():
    X = __import__("pandas").DataFrame({
        "ret_1": [0.1, -0.2, 0.3],
        "ret_3": [0.2, -0.1, 0.4],
        "ret_5": [0.3, -0.2, 0.5],
        "vol_5": [0.5, 0.7, 0.4],
        "vol_20": [1.0, 1.2, 0.9],
        "volume_ratio_5": [1.5, 0.8, 2.0],
        "range_pct": [1.0, 1.2, 1.1],
        "close_vs_avg_pct": [0.2, -0.1, 0.3],
    })
    score = SkyRuleBaseline().fit(X).predict(X)
    assert len(score) == 3

    metrics = evaluate_predictions(
        [1.5, -0.5, 2.0],
        [1.0, -1.0, 0.8],
        BenchmarkConfig(round_trip_cost_pct=0.45, slippage_pct=0.05),
    )
    assert metrics["trades"] == 2
    assert metrics["net_expectancy_pct"] > 0
    assert metrics["profit_factor"] == "inf"

    gate = benchmark_gate(
        {
            "net_expectancy_pct": 0.2,
            "profit_factor": 1.3,
            "max_drawdown_pct": 8.0,
        },
        walk_forward_passed=True,
        cost_stress_passed=True,
        leakage_check_passed=True,
        survivorship_reviewed=True,
        regime_robustness_passed=True,
        paper_trade_passed=False,
    )
    assert gate["production_eligible"] is False
    assert "paper_trade" in gate["failed_checks"]

    passed = benchmark_gate(
        {
            "net_expectancy_pct": 0.2,
            "profit_factor": 1.3,
            "max_drawdown_pct": 8.0,
        },
        walk_forward_passed=True,
        cost_stress_passed=True,
        leakage_check_passed=True,
        survivorship_reviewed=True,
        regime_robustness_passed=True,
        paper_trade_passed=True,
    )
    assert passed["production_eligible"] is True

    print("PASS Model Benchmark Arena tests")


if __name__ == "__main__":
    main()
