from research.feature_ablation_lab import compare_metrics, summarize_candidates
from src.feature_governance import feature_decision, rule_ablation_decision


def main():
    delta = compare_metrics(
        {
            "net_expectancy_pct": 0.20,
            "profit_factor": 1.40,
            "max_drawdown_pct": 7.0,
        },
        {
            "net_expectancy_pct": 0.08,
            "profit_factor": 1.10,
            "max_drawdown_pct": 10.0,
        },
    )
    assert delta["expectancy_contribution"] == 0.12
    assert round(delta["profit_factor_contribution"], 2) == 0.30
    assert delta["drawdown_protection"] == 3.0

    keep = feature_decision(
        expectancy_contribution=0.12,
        profit_factor_contribution=0.20,
        drawdown_protection=1.5,
        regime_consistent=True,
        walk_forward_consistent=True,
    )
    assert keep["status"] == "KEEP"

    prune = feature_decision(
        expectancy_contribution=-0.05,
        profit_factor_contribution=-0.10,
        drawdown_protection=-0.5,
        regime_consistent=False,
        walk_forward_consistent=False,
    )
    assert prune["status"] == "PRUNE_CANDIDATE"

    rule = rule_ablation_decision(
        {
            "net_expectancy_pct": 0.18,
            "profit_factor": 1.35,
            "max_drawdown_pct": 8.0,
        },
        {
            "net_expectancy_pct": 0.10,
            "profit_factor": 1.15,
            "max_drawdown_pct": 11.0,
        },
        regime_consistent=True,
        walk_forward_consistent=True,
    )
    assert rule["status"] == "KEEP"

    report = {
        "single_feature_ablation": {
            "ret_1": {
                "delta_vs_full": {
                    "expectancy_contribution": 0.10,
                    "profit_factor_contribution": 0.05,
                    "drawdown_protection": 0.0,
                }
            },
            "vol_20": {
                "delta_vs_full": {
                    "expectancy_contribution": -0.02,
                    "profit_factor_contribution": -0.01,
                    "drawdown_protection": -0.2,
                }
            },
        }
    }
    rows = summarize_candidates(report)
    assert rows[0]["feature"] == "ret_1"
    assert rows[0]["candidate_action"] == "KEEP_CANDIDATE"
    assert rows[1]["candidate_action"] == "REVIEW_OR_PRUNE"

    print("PASS Feature Importance + Ablation Lab tests")


if __name__ == "__main__":
    main()
