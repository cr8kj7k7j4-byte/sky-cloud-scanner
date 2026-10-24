from __future__ import annotations
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset, metrics


def make_model(name: str, seed=42):
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=250, max_depth=10, min_samples_leaf=10,
            n_jobs=-1, random_state=seed
        )
    if name == "xgboost":
        return XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.04,
            subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
            objective="reg:squarederror", n_jobs=4, random_state=seed
        )
    raise ValueError(name)


def walk_forward(df, model_name, train_days=30, test_days=5, embargo_bars=1):
    df = df.sort_values("date").reset_index(drop=True)
    days = sorted(pd.to_datetime(df["date"]).dt.date.unique())
    rows = []

    i = train_days
    fold = 0
    while i + test_days <= len(days):
        train_start = days[i - train_days]
        train_end = days[i - 1]
        test_start = days[i]
        test_end = days[i + test_days - 1]

        train = df[
            (pd.to_datetime(df["date"]).dt.date >= train_start) &
            (pd.to_datetime(df["date"]).dt.date <= train_end)
        ].copy()
        test = df[
            (pd.to_datetime(df["date"]).dt.date >= test_start) &
            (pd.to_datetime(df["date"]).dt.date <= test_end)
        ].copy()

        # Embargo removes the most recent training rows near test boundary.
        if embargo_bars > 0 and len(train) > embargo_bars:
            train = train.iloc[:-embargo_bars]

        if len(train) < 100 or len(test) < 20:
            i += test_days
            continue

        model = make_model(model_name, 42 + fold)
        model.fit(train[FEATURE_COLS], train["target_return_pct"])
        pred = model.predict(test[FEATURE_COLS])
        m = metrics(test["target_return_pct"], pred)
        rows.append({
            "fold": fold,
            "train_start": str(train_start),
            "train_end": str(train_end),
            "test_start": str(test_start),
            "test_end": str(test_end),
            **m,
        })
        fold += 1
        i += test_days

    return rows


def summarize(rows):
    if not rows:
        return {"folds": 0, "passed": False, "reason": "insufficient folds"}
    weights = np.array([r["n"] for r in rows], dtype=float)
    da = np.average([r["directional_accuracy"] for r in rows], weights=weights)
    mae = np.average([r["mae"] for r in rows], weights=weights)
    return {
        "folds": len(rows),
        "weighted_directional_accuracy": float(da),
        "weighted_mae": float(mae),
        "passed": bool(len(rows) >= 3 and da > 0.52),
        "threshold_note": "Research gate only; >52% directional accuracy is not sufficient for production by itself.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--out", default="research_output/walk_forward.json")
    ap.add_argument("--train-days", type=int, default=30)
    ap.add_argument("--test-days", type=int, default=5)
    args = ap.parse_args()

    df = load_dataset(args.dataset).dropna(subset=FEATURE_COLS + ["target_return_pct"])
    report = {"models": {}}
    for name in ["random_forest", "xgboost"]:
        folds = walk_forward(df, name, args.train_days, args.test_days)
        report["models"][name] = {
            "summary": summarize(folds),
            "folds": folds,
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
