from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


RULE_COLUMNS = [
    "market_gate",
    "sector_rs_gate",
    "anti_chase_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "rr_gate",
]


def _profit_factor(values):
    vals = np.asarray(values, dtype=float)
    gains = vals[vals > 0].sum()
    losses = abs(vals[vals < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown_r(values):
    vals = np.asarray(values, dtype=float)
    if vals.size == 0:
        return 0.0
    equity = np.cumsum(vals)
    peaks = np.maximum.accumulate(equity)
    return float(abs((equity - peaks).min()))


def _metrics(df):
    r = pd.to_numeric(df["net_r"], errors="coerce").dropna().to_numpy(float)
    if r.size == 0:
        return {"n":0,"expectancy_r":0.0,"profit_factor":0.0,"max_drawdown_r":0.0}
    pf = _profit_factor(r)
    return {
        "n": int(r.size),
        "expectancy_r": round(float(r.mean()), 6),
        "profit_factor": round(pf, 6) if np.isfinite(pf) else "inf",
        "max_drawdown_r": round(_max_drawdown_r(r), 6),
    }


def _apply_rules(df, disabled=None):
    disabled = set(disabled or [])
    mask = pd.Series(True, index=df.index)
    for rule in RULE_COLUMNS:
        if rule in disabled:
            continue
        if rule not in df.columns:
            raise ValueError(f"missing rule column: {rule}")
        mask &= df[rule].astype(bool)
    return df[mask].copy()


def _pf(v):
    return 999.0 if v == "inf" else float(v or 0.0)


def contribution(full, ablated):
    return {
        "expectancy_contribution": round(
            float(full["expectancy_r"]) - float(ablated["expectancy_r"]), 6
        ),
        "profit_factor_contribution": round(
            _pf(full["profit_factor"]) - _pf(ablated["profit_factor"]), 6
        ),
        "drawdown_protection": round(
            abs(float(ablated["max_drawdown_r"])) - abs(float(full["max_drawdown_r"])),
            6,
        ),
    }


def walk_forward_windows(df, train_days=30, test_days=5):
    if "date" not in df.columns:
        raise ValueError("date column required")
    x = df.copy()
    x["date"] = pd.to_datetime(x["date"])
    days = sorted(x["date"].dt.date.unique())
    windows = []
    i = train_days
    fold = 0
    while i + test_days <= len(days):
        test_start = days[i]
        test_end = days[i + test_days - 1]
        part = x[
            (x["date"].dt.date >= test_start)
            & (x["date"].dt.date <= test_end)
        ].copy()
        if not part.empty:
            windows.append((fold, str(test_start), str(test_end), part))
            fold += 1
        i += test_days
    return windows


def evaluate_rule_by_fold(df, rule, train_days=30, test_days=5):
    rows = []
    for fold, start, end, part in walk_forward_windows(df, train_days, test_days):
        full = _metrics(_apply_rules(part))
        ablated = _metrics(_apply_rules(part, disabled=[rule]))
        delta = contribution(full, ablated)
        rows.append({
            "fold": fold,
            "test_start": start,
            "test_end": end,
            "full": full,
            "without_rule": ablated,
            "delta": delta,
        })
    return rows


def evaluate_rule_by_regime(df, rule):
    if "regime" not in df.columns:
        return {}
    out = {}
    for regime, part in df.groupby("regime"):
        full = _metrics(_apply_rules(part))
        ablated = _metrics(_apply_rules(part, disabled=[rule]))
        out[str(regime)] = {
            "full": full,
            "without_rule": ablated,
            "delta": contribution(full, ablated),
        }
    return out


def summarize_stability(folds, regimes, min_samples=30):
    fold_exp = [x["delta"]["expectancy_contribution"] for x in folds if x["full"]["n"] > 0]
    fold_positive_share = (
        float(np.mean(np.asarray(fold_exp) > 0)) if fold_exp else 0.0
    )
    regime_exp = [
        x["delta"]["expectancy_contribution"]
        for x in regimes.values()
        if x["full"]["n"] >= min_samples
    ]
    regime_positive_share = (
        float(np.mean(np.asarray(regime_exp) > 0)) if regime_exp else 0.0
    )
    total_n = sum(x["full"]["n"] for x in folds)

    return {
        "fold_count": len(folds),
        "fold_positive_share": round(fold_positive_share, 6),
        "regime_count": len(regime_exp),
        "regime_positive_share": round(regime_positive_share, 6),
        "sample_n": int(total_n),
        "walk_forward_consistent": bool(len(folds) >= 3 and fold_positive_share >= 0.67),
        "regime_consistent": bool(len(regime_exp) >= 2 and regime_positive_share >= 0.67),
        "sample_sufficient": bool(total_n >= min_samples),
    }


def classify(summary):
    if (
        summary["walk_forward_consistent"]
        and summary["regime_consistent"]
        and summary["sample_sufficient"]
    ):
        return "STABLE"
    if summary["sample_sufficient"]:
        return "MIXED"
    return "INSUFFICIENT_SAMPLE"


def build_matrix(df, train_days=30, test_days=5, min_samples=30):
    matrix = {}
    for rule in RULE_COLUMNS:
        folds = evaluate_rule_by_fold(df, rule, train_days, test_days)
        regimes = evaluate_rule_by_regime(df, rule)
        summary = summarize_stability(folds, regimes, min_samples=min_samples)
        matrix[rule] = {
            "summary": summary,
            "status": classify(summary),
            "folds": folds,
            "regimes": regimes,
        }
    return {
        "rules": matrix,
        "production_eligible": False,
        "note": (
            "Stability matrix is research evidence only. Stable does not mean "
            "profitable in the future and does not authorize automatic rule changes."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default="research_output/rule_stability_matrix.json")
    ap.add_argument("--train-days", type=int, default=30)
    ap.add_argument("--test-days", type=int, default=5)
    ap.add_argument("--min-samples", type=int, default=30)
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    report = build_matrix(
        df,
        train_days=args.train_days,
        test_days=args.test_days,
        min_samples=args.min_samples,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
