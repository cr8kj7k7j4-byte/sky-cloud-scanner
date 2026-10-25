from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset, time_split


FEATURE_GROUPS = {
    "momentum": ["ret_1", "ret_3", "ret_5"],
    "volatility": ["vol_5", "vol_20", "range_pct"],
    "volume": ["volume_ratio_5"],
    "price_vs_avg": ["close_vs_avg_pct"],
}


@dataclass(frozen=True)
class AblationConfig:
    round_trip_cost_pct: float = 0.45
    slippage_pct: float = 0.05
    signal_threshold: float = 0.0
    random_state: int = 42


def make_model(name: str, seed=42):
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=10,
            n_jobs=-1,
            random_state=seed,
        )
    if name == "xgboost":
        return XGBRegressor(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=2.0,
            objective="reg:squarederror",
            n_jobs=4,
            random_state=seed,
        )
    raise ValueError(f"unsupported model: {name}")


def _profit_factor(returns):
    vals = np.asarray(returns, dtype=float)
    gains = vals[vals > 0].sum()
    losses = abs(vals[vals < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown_pct(returns):
    vals = np.asarray(returns, dtype=float) / 100.0
    if vals.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + vals)
    peaks = np.maximum.accumulate(equity)
    dd = equity / peaks - 1.0
    return float(abs(dd.min()) * 100.0)


def evaluate_strategy(y_true, pred, config=None):
    config = config or AblationConfig()
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(pred, dtype=float)
    active = p > config.signal_threshold
    total_cost = config.round_trip_cost_pct + config.slippage_pct
    strategy = np.where(active, y - total_cost, 0.0)
    trades = strategy[active]

    expectancy = float(trades.mean()) if trades.size else 0.0
    pf = _profit_factor(trades)
    return {
        "trades": int(active.sum()),
        "trade_rate": round(float(active.mean()) if len(active) else 0.0, 6),
        "net_expectancy_pct": round(expectancy, 6),
        "profit_factor": round(pf, 6) if np.isfinite(pf) else "inf",
        "max_drawdown_pct": round(_max_drawdown_pct(strategy), 6),
    }


def feature_importance_report(model, X_test, y_test, repeats=8, seed=42):
    result = permutation_importance(
        model,
        X_test,
        y_test,
        scoring="neg_mean_absolute_error",
        n_repeats=repeats,
        random_state=seed,
        n_jobs=-1,
    )
    rows = []
    for name, mean_imp, std_imp in zip(
        X_test.columns, result.importances_mean, result.importances_std
    ):
        rows.append({
            "feature": name,
            "importance_mean": round(float(mean_imp), 8),
            "importance_std": round(float(std_imp), 8),
        })
    rows.sort(key=lambda x: x["importance_mean"], reverse=True)
    return rows


def run_ablation(df, model_name="xgboost", config=None):
    config = config or AblationConfig()
    df = df.dropna(subset=FEATURE_COLS + ["target_return_pct"]).copy()
    train, val, test = time_split(df)

    def fit_eval(features, seed):
        model = make_model(model_name, seed)
        model.fit(train[features], train["target_return_pct"])
        pred = model.predict(test[features])
        metrics = evaluate_strategy(test["target_return_pct"], pred, config)
        return model, metrics

    full_model, full_metrics = fit_eval(FEATURE_COLS, config.random_state)
    importance = feature_importance_report(
        full_model,
        test[FEATURE_COLS],
        test["target_return_pct"],
        seed=config.random_state,
    )

    groups = {}
    for idx, (group, members) in enumerate(FEATURE_GROUPS.items(), start=1):
        reduced = [f for f in FEATURE_COLS if f not in members]
        _, metrics = fit_eval(reduced, config.random_state + idx)
        groups[group] = {
            "removed_features": members,
            "remaining_features": reduced,
            "metrics": metrics,
            "delta_vs_full": compare_metrics(full_metrics, metrics),
        }

    single = {}
    for idx, feature in enumerate(FEATURE_COLS, start=20):
        reduced = [f for f in FEATURE_COLS if f != feature]
        _, metrics = fit_eval(reduced, config.random_state + idx)
        single[feature] = {
            "metrics": metrics,
            "delta_vs_full": compare_metrics(full_metrics, metrics),
        }

    return {
        "model": model_name,
        "full_features": FEATURE_COLS,
        "full_metrics": full_metrics,
        "permutation_importance": importance,
        "group_ablation": groups,
        "single_feature_ablation": single,
        "production_eligible": False,
        "note": (
            "Importance is not causation. Ablation results are research evidence only "
            "and require Walk-forward/OOS/regime consistency before rule changes."
        ),
    }


def compare_metrics(full, ablated):
    full_exp = float(full.get("net_expectancy_pct") or 0.0)
    abl_exp = float(ablated.get("net_expectancy_pct") or 0.0)

    def pf(v):
        return 999.0 if v == "inf" else float(v or 0.0)

    full_pf = pf(full.get("profit_factor"))
    abl_pf = pf(ablated.get("profit_factor"))
    full_dd = abs(float(full.get("max_drawdown_pct") or 0.0))
    abl_dd = abs(float(ablated.get("max_drawdown_pct") or 0.0))

    return {
        "expectancy_contribution": round(full_exp - abl_exp, 6),
        "profit_factor_contribution": round(full_pf - abl_pf, 6),
        "drawdown_protection": round(abl_dd - full_dd, 6),
        "interpretation": (
            "Positive expectancy/PF contribution suggests the removed component added value. "
            "Positive drawdown protection suggests removing it worsened drawdown."
        ),
    }


def summarize_candidates(report, min_expectancy_contribution=0.0):
    rows = []
    for feature, item in report.get("single_feature_ablation", {}).items():
        delta = item["delta_vs_full"]
        rows.append({
            "feature": feature,
            "expectancy_contribution": delta["expectancy_contribution"],
            "profit_factor_contribution": delta["profit_factor_contribution"],
            "drawdown_protection": delta["drawdown_protection"],
            "candidate_action": (
                "KEEP_CANDIDATE"
                if delta["expectancy_contribution"] > min_expectancy_contribution
                else "REVIEW_OR_PRUNE"
            ),
        })
    rows.sort(key=lambda x: x["expectancy_contribution"], reverse=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--out", default="research_output/feature_ablation_lab.json")
    ap.add_argument("--model", choices=["random_forest", "xgboost"], default="xgboost")
    args = ap.parse_args()

    df = load_dataset(args.dataset)
    report = run_ablation(df, model_name=args.model)
    report["feature_review"] = summarize_candidates(report)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
