from src.validation_engine import (
    CostScenario,
    ablation_delta,
    aggregate_by_regime,
    cost_stress_report,
    leakage_audit,
    regime_bucket,
)


def main():
    report = cost_stress_report(
        [1.2, 0.9, 1.5],
        [
            CostScenario("BASE", 0.45, 0.05),
            CostScenario("STRESS", 0.60, 0.10),
        ],
    )
    assert report["passed"] is True
    assert report["scenarios"][0]["net_expectancy_pct"] > 0

    bad = leakage_audit(
        ["ret_1", "future_return", "target_return_pct"],
        ["target_return_pct"],
        {"timestamp_order_ok": True, "survivorship_reviewed": True},
    )
    assert bad["passed"] is False
    assert "target_return_pct" in bad["feature_target_overlap"]

    good = leakage_audit(
        ["ret_1", "ret_5", "volume_ratio_5"],
        ["target_return_pct"],
        {"timestamp_order_ok": True, "survivorship_reviewed": True},
    )
    assert good["passed"] is True

    assert regime_bucket(1.5, 3.0) == "BULL_HIGH"
    regimes = aggregate_by_regime([
        {"regime": "BULL_HIGH", "net_r": 1.0},
        {"regime": "BULL_HIGH", "net_r": -0.2},
        {"regime": "BEAR_HIGH", "net_r": -0.5},
    ])
    assert regimes["BULL_HIGH"]["expectancy_r"] == 0.4
    assert regimes["BEAR_HIGH"]["expectancy_r"] == -0.5

    delta = ablation_delta(
        {"expectancy_r": 0.12, "profit_factor": 1.30, "max_drawdown_r": 3.0},
        {"expectancy_r": 0.04, "profit_factor": 1.05, "max_drawdown_r": 4.5},
    )
    assert delta["expectancy_r"] == 0.08
    assert delta["profit_factor"] == 0.25
    assert delta["max_drawdown_r"] == 1.5

    print("PASS Phase 3 validation engine tests")


if __name__ == "__main__":
    main()
