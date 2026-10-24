from __future__ import annotations
import argparse, json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from research.build_ml_dataset import FEATURE_COLS


def load_dataset(path: str):
    p = Path(path)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    return pd.read_csv(p, parse_dates=["date"])


def directional_accuracy(y_true, y_pred):
    a = np.asarray(y_true)
    b = np.asarray(y_pred)
    return float(np.mean(np.sign(a) == np.sign(b)))


def metrics(y_true, y_pred):
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "directional_accuracy": directional_accuracy(y_true, y_pred),
        "n": int(len(y_true)),
    }


def time_split(df, train_ratio=0.70, val_ratio=0.15):
    df = df.sort_values("date").reset_index(drop=True)
    dates = sorted(pd.Series(df["date"]).drop_duplicates())
    if len(dates) < 10:
        raise ValueError("Not enough unique timestamps for time split")

    train_end = dates[max(1, int(len(dates) * train_ratio)) - 1]
    val_end = dates[max(2, int(len(dates) * (train_ratio + val_ratio))) - 1]

    train = df[df["date"] <= train_end]
    val = df[(df["date"] > train_end) & (df["date"] <= val_end)]
    test = df[df["date"] > val_end]
    if min(len(train), len(val), len(test)) == 0:
        raise ValueError("Time split produced an empty partition")
    return train, val, test


def build_models(seed=42):
    return {
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=10,
            n_jobs=-1,
            random_state=seed,
        ),
        "xgboost": XGBRegressor(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=2.0,
            objective="reg:squarederror",
            random_state=seed,
            n_jobs=4,
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--out", default="research_output/models")
    ap.add_argument("--target", default="target_return_pct")
    args = ap.parse_args()

    df = load_dataset(args.dataset).dropna(subset=FEATURE_COLS + [args.target]).copy()
    train, val, test = time_split(df)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    X_train, y_train = train[FEATURE_COLS], train[args.target]
    X_val, y_val = val[FEATURE_COLS], val[args.target]
    X_test, y_test = test[FEATURE_COLS], test[args.target]

    report = {
        "target": args.target,
        "features": FEATURE_COLS,
        "split": {
            "train_n": len(train), "val_n": len(val), "test_n": len(test),
            "train_max_date": str(train["date"].max()),
            "val_max_date": str(val["date"].max()),
            "test_max_date": str(test["date"].max()),
        },
        "models": {},
        "production_eligible": False,
        "note": "Training artifact only. Walk-forward, OOS, cost stress, leakage checks and paper trading remain mandatory.",
    }

    for name, model in build_models().items():
        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        test_pred = model.predict(X_test)
        report["models"][name] = {
            "validation": metrics(y_val, val_pred),
            "holdout_test": metrics(y_test, test_pred),
        }
        joblib.dump(model, out / f"{name}.joblib")

    (out / "metadata.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
