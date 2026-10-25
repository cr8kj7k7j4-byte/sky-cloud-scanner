from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from xgboost import XGBRegressor

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset, time_split


@dataclass(frozen=True)
class BenchmarkConfig:
    round_trip_cost_pct: float = 0.45
    slippage_pct: float = 0.05
    signal_threshold: float = 0.0
    chunks_for_stability: int = 4


class SkyRuleBaseline:
    """
    Transparent research baseline.
    The score is not a probability and must not be presented as one.
    """
    def fit(self, X, y=None):
        return self

    def predict(self, X):
        cols = set(X.columns)
        score = np.zeros(len(X), dtype=float)
        if "ret_1" in cols:
            score += 0.20 * X["ret_1"].to_numpy(float)
        if "ret_3" in cols:
            score += 0.25 * X["ret_3"].to_numpy(float)
        if "ret_5" in cols:
            score += 0.35 * X["ret_5"].to_numpy(float)
        if "volume_ratio_5" in cols:
            score += 0.30 * (X["volume_ratio_5"].to_numpy(float) - 1.0)
        if "close_vs_avg_pct" in cols:
            score -= 0.10 * np.abs(X["close_vs_avg_pct"].to_numpy(float))
        if "vol_20" in cols:
            score -= 0.05 * np.abs(X["vol_20"].to_numpy(float))
        return score


class LogisticDirectionModel:
    """
    Direction model. predict() returns signed conviction around zero,
    not an estimated return and not a trading win probability.
    """
    def __init__(self, seed=42):
        self.model = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=seed,
        )

    def fit(self, X, y):
        target = (np.asarray(y) > 0).astype(int)
        self.model.fit(X, target)
        return self

    def predict(self, X):
        p = self.model.predict_proba(X)[:, 1]
        return p - 0.5


def make_model(name: str, seed=42):
    if name == "sky_rule_engine":
        return SkyRuleBaseline()
    if name == "logistic_regression":
        return LogisticDirectionModel(seed)
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
    if name == "lightgbm":
        try:
            from lightgbm import LGBMRegressor
        except ImportError as e:
            raise RuntimeError(
                "lightgbm is required for the LightGBM benchmark. "
                "Install requirements-ml.txt."
            ) from e
        return LGBMRegressor(
            n_estimators=400,
            max_depth=-1,
            num_leaves=31,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=2.0,
            random_state=seed,
            verbosity=-1,
        )
    raise ValueError(f"unknown model: {name}")


def max_drawdown_from_returns(returns_pct):
    vals = np.asarray(list(returns_pct), dtype=float) / 100.0
    if vals.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + vals)
    peaks = np.maximum.accumulate(equity)
    dd = equity / peaks - 1.0
    return float(abs(dd.min()) * 100.0)


def profit_factor(returns_pct):
    vals = np.asarray(list(returns_pct), dtype=float)
    gains = vals[vals > 0].sum()
    losses = abs(vals[vals < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def stability_score(returns_pct, chunks=4):
    vals = np.asarray(list(returns_pct), dtype=float)
    if vals.size < chunks:
        return 0.0
    groups = np.array_split(vals, chunks)
    means = np.array([x.mean() if len(x) else 0.0 for x in groups], dtype=float)
    positive_share = float(np.mean(means > 0))
    dispersion = float(np.std(means))
    return max(0.0, positive_share - min(dispersion / 5.0, 1.0))


def evaluate_predictions(y_true, prediction_score, config=None):
    config = config or BenchmarkConfig()
    y = np.asarray(y_true, dtype=float)
    pred = np.asarray(prediction_score, dtype=float)
    active = pred > config.signal_threshold

    total_cost = config.round_trip_cost_pct + config.slippage_pct
    strategy = np.where(active, y - total_cost, 0.0)

    active_returns = strategy[active]
    expectancy = float(active_returns.mean()) if active_returns.size else 0.0
    pf = profit_factor(active_returns)
    mdd = max_drawdown_from_returns(strategy)
    stability = stability_score(active_returns, config.chunks_for_stability)

    return {
        "n": int(len(y)),
        "trades": int(active.sum()),
        "trade_rate": round(float(active.mean()) if len(active) else 0.0, 6),
        "net_expectancy_pct": round(expectancy, 6),
        "profit_factor": round(pf, 6) if np.isfinite(pf) else "inf",
        "max_drawdown_pct": round(mdd, 6),
        "stability_score": round(stability, 6),
        "positive_trade_rate": round(
            float(np.mean(active_returns > 0)) if active_returns.size else 0.0,
            6,
        ),
        "round_trip_cost_pct": config.round_trip_cost_pct,
        "slippage_pct": config.slippage_pct,
        "note": "positive_trade_rate is descriptive only; it is not a forecast probability.",
    }


def run_benchmark(df, config=None, seed=42):
    config = config or BenchmarkConfig()
    df = df.dropna(subset=FEATURE_COLS + ["target_return_pct"]).copy()
    train, val, test = time_split(df)

    X_train = train[FEATURE_COLS]
    y_train = train["target_return_pct"]
    X_val = val[FEATURE_COLS]
    y_val = val["target_return_pct"]
    X_test = test[FEATURE_COLS]
    y_test = test["target_return_pct"]

    names = [
        "sky_rule_engine",
        "logistic_regression",
        "random_forest",
        "xgboost",
        "lightgbm",
    ]
    report = {
        "config": config.__dict__,
        "split": {
            "train_n": len(train),
            "validation_n": len(val),
            "oos_n": len(test),
            "train_end": str(train["date"].max()),
            "validation_end": str(val["date"].max()),
            "oos_end": str(test["date"].max()),
        },
        "models": {},
        "production_eligible": False,
        "note": (
            "Benchmark evidence only. Production promotion still requires "
            "Walk-forward, regime robustness, leakage/survivorship review, "
            "cost stress, and paper trading."
        ),
    }

    for idx, name in enumerate(names):
        model = make_model(name, seed + idx)
        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        test_pred = model.predict(X_test)
        report["models"][name] = {
            "validation": evaluate_predictions(y_val, val_pred, config),
            "oos": evaluate_predictions(y_test, test_pred, config),
        }

    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--out", default="research_output/model_benchmark_arena.json")
    ap.add_argument("--round-trip-cost-pct", type=float, default=0.45)
    ap.add_argument("--slippage-pct", type=float, default=0.05)
    args = ap.parse_args()

    df = load_dataset(args.dataset)
    config = BenchmarkConfig(
        round_trip_cost_pct=args.round_trip_cost_pct,
        slippage_pct=args.slippage_pct,
    )
    report = run_benchmark(df, config=config)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
