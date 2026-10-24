from __future__ import annotations
import argparse, json
from pathlib import Path

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset


FORBIDDEN_TOKENS = ("target_", "future_", "label_")


def audit_dataset(df):
    feature_name_check = all(
        not any(token in c.lower() for token in FORBIDDEN_TOKENS)
        for c in FEATURE_COLS
    )
    required_present = all(c in df.columns for c in FEATURE_COLS + ["target_return_pct", "date", "symbol"])
    no_feature_target_overlap = not set(FEATURE_COLS).intersection(
        {"target_return_pct", "target_mfe_pct", "target_mae_pct"}
    )
    chronological = bool(len(df) == 0 or df.sort_values("date")["date"].is_monotonic_increasing)
    finite_target_share = float(df["target_return_pct"].notna().mean()) if "target_return_pct" in df else 0.0

    checks = {
        "feature_name_check": feature_name_check,
        "required_columns_present": required_present,
        "no_feature_target_overlap": no_feature_target_overlap,
        "chronological_sort_check": chronological,
        "target_non_null_share_ge_95pct": finite_target_share >= 0.95,
    }
    return {
        "checks": checks,
        "target_non_null_share": finite_target_share,
        "passed": all(checks.values()),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "note": (
            "This audit checks the dataset contract and obvious feature/label leakage. "
            "It does not replace independent code review, purging/embargo design, or OOS testing."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--out", default="research_output/leakage_audit.json")
    args = ap.parse_args()

    df = load_dataset(args.dataset)
    report = audit_dataset(df)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
