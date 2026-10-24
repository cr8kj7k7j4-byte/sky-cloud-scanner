from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from src.validation_engine import (
    DEFAULT_COST_SCENARIOS,
    ablation_delta,
    aggregate_by_regime,
    cost_stress_report,
    leakage_audit,
)
from research.build_ml_dataset import FEATURE_COLS


def load_csv(path):
    return pd.read_csv(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True, help="CSV with gross_return_pct, net_r, market_return_pct, volatility_pct")
    ap.add_argument("--out", default="research_output/phase3_validation.json")
    args = ap.parse_args()

    df = load_csv(args.predictions)

    gross = df["gross_return_pct"].dropna().tolist() if "gross_return_pct" in df else []
    regime_records = df.to_dict("records")

    leakage = leakage_audit(
        FEATURE_COLS,
        ["target_return_pct", "target_mfe_pct", "target_mae_pct"],
        {
            "timestamp_order_ok": True,
            "survivorship_reviewed": bool("survivorship_reviewed" in df.columns and df["survivorship_reviewed"].all()),
        },
    )

    report = {
        "cost_stress": cost_stress_report(gross, DEFAULT_COST_SCENARIOS),
        "leakage_audit": leakage,
        "regime": aggregate_by_regime(regime_records),
        "ablation_contract": {
            "required": True,
            "note": "Each gate/feature family must be compared against the full model with identical split/cost assumptions.",
        },
        "production_eligible": False,
        "note": "This runner produces research evidence only. Paper Trading and complete validation gates remain mandatory.",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
