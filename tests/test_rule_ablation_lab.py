import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from research.rule_ablation_lab import run_rule_ablation, classify_rule
from src.rule_governance import rule_governance_decision


def main():
    rows = []
    for i, r in enumerate([1.0, 0.8, -0.4, 1.2, -0.2, 0.7]):
        rows.append({
            "market_gate": True,
            "sector_rs_gate": True,
            "anti_chase_gate": i != 2,
            "phase_gate": True,
            "setup_gate": True,
            "trigger_gate": True,
            "rr_gate": True,
            "net_r": r,
            "regime": "BULL" if i < 4 else "NEUTRAL",
        })
    df = pd.DataFrame(rows)
    report = run_rule_ablation(df)
    assert report["full_metrics"]["n"] == 5
    assert "anti_chase_gate" in report["single_rule_ablation"]

    delta = report["single_rule_ablation"]["anti_chase_gate"]["delta_vs_full"]
    assert isinstance(delta["expectancy_contribution"], float)

    status = classify_rule(
        {
            "expectancy_contribution": 0.10,
            "profit_factor_contribution": 0.20,
            "drawdown_protection": 0.30,
        },
        regime_consistent=True,
        walk_forward_consistent=True,
    )
    assert status == "KEEP"

    governed = rule_governance_decision(
        "anti_chase_gate",
        expectancy_contribution=0.10,
        profit_factor_contribution=0.20,
        drawdown_protection=0.30,
        regime_consistent=True,
        walk_forward_consistent=True,
        sample_sufficient=True,
    )
    assert governed["status"] == "KEEP"
    assert governed["production_change_allowed"] is False

    print("PASS Rule / Gate Ablation Lab tests")


if __name__ == "__main__":
    main()
