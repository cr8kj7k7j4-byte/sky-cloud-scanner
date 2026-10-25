from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.intraday_replay_validator import CANONICAL_RULE_COLUMNS
from research.intraday_rule_ablation import (
    apply_rules,
    contribution,
    evaluate_subset,
)


COST_COLUMNS = {
    "primary_045": "net_r_045",
    "stress_065": "net_r_065",
}


def walk_forward_windows(
    df: pd.DataFrame,
    *,
    warmup_days: int = 30,
    test_days: int = 5,
) -> list[tuple[int, str, str, pd.DataFrame]]:
    x = df.copy()
    if "session_date" in x.columns:
        x["_date"] = pd.to_datetime(x["session_date"], errors="coerce").dt.date
    elif "decision_timestamp" in x.columns:
        x["_date"] = pd.to_datetime(x["decision_timestamp"], errors="coerce").dt.date
    else:
        raise ValueError("session_date or decision_timestamp required")

    x = x[x["_date"].notna()].copy()
    days = sorted(x["_date"].unique())
    windows = []
    i = warmup_days
    fold = 0
    while i + test_days <= len(days):
        start = days[i]
        end = days[i + test_days - 1]
        part = x[(x["_date"] >= start) & (x["_date"] <= end)].copy()
        if not part.empty:
            windows.append((fold, str(start), str(end), part))
            fold += 1
        i += test_days
    return windows


def _positive(delta: dict) -> bool:
    return float(delta.get("expectancy_contribution") or 0.0) > 0.0


def _evaluate_rule_on_part(
    part: pd.DataFrame,
    *,
    rule: str,
    outcome_column: str,
) -> dict:
    full = evaluate_subset(apply_rules(part), outcome_column)
    without = evaluate_subset(
        apply_rules(part, disabled=[rule]),
        outcome_column,
    )
    return {
        "full": full,
        "without_rule": without,
        "delta": contribution(full, without),
    }


def evaluate_folds(
    df: pd.DataFrame,
    *,
    rule: str,
    outcome_column: str,
    warmup_days: int,
    test_days: int,
) -> list[dict]:
    rows = []
    for fold, start, end, part in walk_forward_windows(
        df,
        warmup_days=warmup_days,
        test_days=test_days,
    ):
        item = _evaluate_rule_on_part(
            part,
            rule=rule,
            outcome_column=outcome_column,
        )
        item.update(
            {
                "fold": fold,
                "test_start": start,
                "test_end": end,
            }
        )
        rows.append(item)
    return rows


def evaluate_regimes(
    df: pd.DataFrame,
    *,
    rule: str,
    outcome_column: str,
) -> dict:
    if "market_regime" not in df.columns:
        return {}
    out = {}
    for regime, part in df.groupby("market_regime", dropna=False):
        out[str(regime)] = _evaluate_rule_on_part(
            part,
            rule=rule,
            outcome_column=outcome_column,
        )
    return out


def summarize(
    folds: list[dict],
    regimes: dict,
    *,
    min_fold_n: int = 30,
    min_regime_n: int = 30,
) -> dict:
    eligible_folds = [x for x in folds if int(x["full"]["n"]) >= min_fold_n]
    eligible_regimes = [
        x for x in regimes.values()
        if int(x["full"]["n"]) >= min_regime_n
    ]

    fold_positive_share = (
        float(np.mean([_positive(x["delta"]) for x in eligible_folds]))
        if eligible_folds
        else 0.0
    )
    regime_positive_share = (
        float(np.mean([_positive(x["delta"]) for x in eligible_regimes]))
        if eligible_regimes
        else 0.0
    )

    fold_dd_share = (
        float(
            np.mean(
                [
                    float(x["delta"].get("drawdown_protection") or 0.0) > 0
                    for x in eligible_folds
                ]
            )
        )
        if eligible_folds
        else 0.0
    )

    return {
        "eligible_fold_count": len(eligible_folds),
        "fold_positive_share": round(fold_positive_share, 6),
        "fold_drawdown_protection_share": round(fold_dd_share, 6),
        "eligible_regime_count": len(eligible_regimes),
        "regime_positive_share": round(regime_positive_share, 6),
        "walk_forward_consistent": bool(
            len(eligible_folds) >= 3 and fold_positive_share >= 0.67
        ),
        "regime_consistent": bool(
            len(eligible_regimes) >= 2 and regime_positive_share >= 0.67
        ),
    }


def classify_rule(primary: dict, stress: dict) -> str:
    p = primary["summary"]
    s = stress["summary"]

    if (
        p["walk_forward_consistent"]
        and p["regime_consistent"]
        and s["walk_forward_consistent"]
        and s["regime_consistent"]
    ):
        return "STABLE"

    p_folds = primary["folds"]
    s_folds = stress["folds"]
    eligible_count = min(
        p["eligible_sample_evidence"],
        s["eligible_sample_evidence"],
    )
    if eligible_count == 0:
        return "INSUFFICIENT_SAMPLE"

    p_negative = p_folds and all(
        float(x["delta"]["expectancy_contribution"]) < 0
        and float(x["delta"]["drawdown_protection"]) <= 0
        for x in p_folds
        if x["full"]["n"] > 0
    )
    s_negative = s_folds and all(
        float(x["delta"]["expectancy_contribution"]) < 0
        and float(x["delta"]["drawdown_protection"]) <= 0
        for x in s_folds
        if x["full"]["n"] > 0
    )
    if p_negative and s_negative:
        return "NEGATIVE"

    return "MIXED"


def build_rule_evidence(
    df: pd.DataFrame,
    *,
    rule: str,
    outcome_column: str,
    warmup_days: int,
    test_days: int,
    min_fold_n: int,
    min_regime_n: int,
) -> dict:
    folds = evaluate_folds(
        df,
        rule=rule,
        outcome_column=outcome_column,
        warmup_days=warmup_days,
        test_days=test_days,
    )
    regimes = evaluate_regimes(
        df,
        rule=rule,
        outcome_column=outcome_column,
    )
    summary = summarize(
        folds,
        regimes,
        min_fold_n=min_fold_n,
        min_regime_n=min_regime_n,
    )
    summary["eligible_sample_evidence"] = (
        summary["eligible_fold_count"] + summary["eligible_regime_count"]
    )
    return {
        "summary": summary,
        "folds": folds,
        "regimes": regimes,
    }


def build_stability_matrix(
    df: pd.DataFrame,
    *,
    warmup_days: int = 30,
    test_days: int = 5,
    min_fold_n: int = 30,
    min_regime_n: int = 30,
) -> dict:
    rules = {}
    for rule in CANONICAL_RULE_COLUMNS:
        cost_evidence = {}
        for scenario, outcome_column in COST_COLUMNS.items():
            cost_evidence[scenario] = build_rule_evidence(
                df,
                rule=rule,
                outcome_column=outcome_column,
                warmup_days=warmup_days,
                test_days=test_days,
                min_fold_n=min_fold_n,
                min_regime_n=min_regime_n,
            )

        status = classify_rule(
            {
                **cost_evidence["primary_045"],
                "eligible_sample_evidence": cost_evidence["primary_045"]["summary"][
                    "eligible_sample_evidence"
                ],
            },
            {
                **cost_evidence["stress_065"],
                "eligible_sample_evidence": cost_evidence["stress_065"]["summary"][
                    "eligible_sample_evidence"
                ],
            },
        )
        rules[rule] = {
            "status": status,
            "cost_scenarios": cost_evidence,
        }

    return {
        "rules": rules,
        "cost_scenarios": COST_COLUMNS,
        "production_eligible": False,
        "note": (
            "STABLE means evidence direction is consistent across eligible folds, "
            "regimes and both cost scenarios. It does not authorize Production changes."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default="research_output/intraday_rule_stability.json")
    ap.add_argument("--warmup-days", type=int, default=30)
    ap.add_argument("--test-days", type=int, default=5)
    ap.add_argument("--min-fold-n", type=int, default=30)
    ap.add_argument("--min-regime-n", type=int, default=30)
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    report = build_stability_matrix(
        df,
        warmup_days=args.warmup_days,
        test_days=args.test_days,
        min_fold_n=args.min_fold_n,
        min_regime_n=args.min_regime_n,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
