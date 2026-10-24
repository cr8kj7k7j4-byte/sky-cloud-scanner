import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from research.rule_stability_matrix import build_matrix
from src.rule_stability_governance import stability_governance


def make_df():
    rows = []
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    for i, dt in enumerate(dates):
        rows.append({
            "date": dt.isoformat(),
            "market_gate": True,
            "sector_rs_gate": True,
            "anti_chase_gate": i % 7 != 0,
            "phase_gate": True,
            "setup_gate": True,
            "trigger_gate": True,
            "rr_gate": True,
            "net_r": 0.6 if i % 3 != 0 else -0.2,
            "regime": "BULL" if i < 30 else "NEUTRAL",
        })
    return pd.DataFrame(rows)


def main():
    df = make_df()
    report = build_matrix(df, train_days=20, test_days=10, min_samples=10)
    assert "anti_chase_gate" in report["rules"]
    anti = report["rules"]["anti_chase_gate"]
    assert anti["summary"]["fold_count"] >= 3
    assert anti["summary"]["sample_n"] > 0

    gov = stability_governance(
        "anti_chase_gate",
        fold_positive_share=0.8,
        regime_positive_share=1.0,
        sample_n=100,
    )
    assert gov["status"] == "STABLE_KEEP_CANDIDATE"
    assert gov["production_change_allowed"] is False

    mixed = stability_governance(
        "rr_gate",
        fold_positive_share=0.5,
        regime_positive_share=0.5,
        sample_n=100,
    )
    assert mixed["status"] == "MIXED_RESEARCH_MORE"

    print("PASS Walk-forward Ablation + Regime Stability Matrix tests")


if __name__ == "__main__":
    main()
