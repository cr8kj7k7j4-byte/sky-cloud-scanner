from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research.intraday_replay_validator import validate_replay_frame
from research.intraday_rule_ablation import run_ablation
from research.intraday_rule_stability import build_stability_matrix


def _rule_registry(primary: dict, stress: dict, stability: dict) -> dict:
    stable = []
    mixed = []
    negative = []
    insufficient = []

    for rule, item in stability["rules"].items():
        status = item["status"]
        p_delta = primary["single_rule_ablation"][rule]["delta_vs_full"]
        s_delta = stress["single_rule_ablation"][rule]["delta_vs_full"]
        record = {
            "rule": rule,
            "stability_status": status,
            "primary_045": p_delta,
            "stress_065": s_delta,
        }

        if status == "STABLE":
            stable.append(record)
        elif status == "NEGATIVE":
            negative.append(record)
        elif status == "MIXED":
            mixed.append(record)
        else:
            insufficient.append(record)

    return {
        "stable_rules": stable,
        "mixed_rules": mixed,
        "negative_rules": negative,
        "insufficient_rules": insufficient,
    }


def run_validation(df: pd.DataFrame) -> dict:
    contract = validate_replay_frame(df)
    report = {
        "contract_validation": contract,
        "production_baseline": "Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP",
        "production_change": False,
        "w2_final_status": "HOLD",
    }

    if contract["gate"] != "PASS":
        report.update(
            {
                "ablation_primary_045": None,
                "ablation_stress_065": None,
                "stability_matrix": None,
                "day_trading_strategy_registry": {
                    "production": [
                        {
                            "name": "Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP",
                            "status": "ACTIVE",
                        }
                    ],
                    "candidate": [],
                    "hold": [],
                    "rejected": [],
                    "archived": [],
                    "blocked": [
                        {
                            "name": "Full 10-Rule Intraday Ablation",
                            "reason": contract["reasons"],
                        }
                    ],
                },
                "stable_rules": [],
                "mixed_rules": [],
                "negative_rules": [],
                "outstanding_data_gaps": contract["reasons"],
                "decision_note": (
                    "Replay contract did not pass. No rule efficacy result is emitted. "
                    "W2 remains HOLD / DATA_BLOCKED."
                ),
            }
        )
        return report

    oos = df[df["research_split"].astype(str).str.upper() == "OOS"].copy()
    if oos.empty:
        report.update(
            {
                "ablation_primary_045": None,
                "ablation_stress_065": None,
                "stability_matrix": None,
                "stable_rules": [],
                "mixed_rules": [],
                "negative_rules": [],
                "outstanding_data_gaps": ["NO_OOS_ROWS"],
                "decision_note": "No OOS rows are available; W2 remains HOLD.",
            }
        )
        return report

    report["oos_row_count"] = int(len(oos))
    primary = run_ablation(oos, outcome_column="net_r_045")
    stress = run_ablation(oos, outcome_column="net_r_065")
    stability = build_stability_matrix(oos)
    registry = _rule_registry(primary, stress, stability)

    report.update(
        {
            "ablation_primary_045": primary,
            "ablation_stress_065": stress,
            "stability_matrix": stability,
            **registry,
            "outstanding_data_gaps": [],
            "decision_note": (
                "Research evidence completed. Any PROMOTE_CANDIDATE decision remains "
                "subject to OOS sufficiency, Shadow/Paper and W0/P0-G review."
            ),
        }
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument(
        "--out",
        default="research_output/w2_intraday_validation_report.json",
    )
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    report = run_validation(df)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
