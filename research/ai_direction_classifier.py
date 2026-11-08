"""Standalone research classification baseline. No orders, no Production eligibility.

Training input is a labeled point-in-time table, NEVER a live Fugle request.
Separate horizons need separate datasets and embargo aligned to label horizon.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def split_by_session(df, *, embargo_sessions: int):
    """Chronological train/calibration/OOS, purged by actual label-end availability.

    Required columns: date (signal time), feature_available_at, label_end_at.
    Calendar session embargo is supplemental; true label overlap is purged.
    """
    import pandas as pd

    if embargo_sessions < 1:
        raise ValueError("embargo must cover the forward-label horizon")
    required = {"date", "feature_available_at", "label_end_at"}
    if not required.issubset(df.columns):
        raise ValueError("missing timestamp causality columns")
    for name in required:
        if not pd.api.types.is_datetime64_any_dtype(df[name]) or df[name].dt.tz is None:
            raise ValueError(f"{name} must be timezone-aware")
    if df[list(required)].isna().any().any():
        raise ValueError("missing causal timestamp")
    if (df["feature_available_at"] > df["date"]).any():
        raise ValueError("lookahead feature detected")
    if (df["label_end_at"] <= df["date"]).any():
        raise ValueError("label must end after prediction time")
    days = sorted(df["date"].dt.date.unique())
    if len(days) < 40 + 3 * embargo_sessions:
        raise ValueError("insufficient unique sessions")
    cuts = [int(len(days) * x) for x in (.6, .8)]
    train_days = days[:max(0, cuts[0] - embargo_sessions)]
    calib_days = days[cuts[0]:max(cuts[0], cuts[1] - embargo_sessions)]
    test_days = days[cuts[1]:]
    if not train_days or not calib_days or not test_days:
        raise ValueError("empty temporal partition")
    train, cal, test = (
        df[df["date"].dt.date.isin(d)].copy()
        for d in (train_days, calib_days, test_days)
    )
    # Label outcomes may never cross into the following evaluation split.
    # The end timestamp must be strictly BEFORE the first prediction.
    cal_first = cal["date"].min()
    test_first = test["date"].min()
    train = train[train["label_end_at"] < cal_first].copy()
    cal = cal[cal["label_end_at"] < test_first].copy()
    if min(len(train), len(cal), len(test)) == 0:
        raise ValueError("purging removed entire temporal partition")
    return train, cal, test


def metrics(y, p):
    import numpy as np
    from sklearn.metrics import brier_score_loss, log_loss
    y, p = np.asarray(y), np.asarray(p)
    if len(y) == 0 or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("invalid probability vector")
    ece = 0.0
    for low in np.arange(0, 1, .1):
        mask = (p >= low) & (p < low + .1 if low < .9 else p <= 1)
        if mask.any():
            ece += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return {"n": int(len(y)), "positive_rate": float(y.mean()),
            "brier": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, p, labels=[0,1])),
            "ece_10bin": float(ece),
            "directional_accuracy_at_0_5": float(((p >= .5) == y).mean())}


def train(df, feature_cols, *, horizon, embargo_sessions):
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier

    if horizon not in ("intraday", "next_day"):
        raise ValueError("unsupported horizon")
    if "target_return_pct" not in df or not all(x in df for x in feature_cols):
        raise ValueError("missing features or labels")
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        raise ValueError("timestamps must be parsed")
    if not df["date"].dt.tz:
        raise ValueError("timestamps require timezone")
    if not np.isfinite(df[feature_cols + ["target_return_pct"]].to_numpy(dtype=float)).all():
        raise ValueError("missing/invalid training data")
    train_data, cal_data, test_data = split_by_session(df, embargo_sessions=embargo_sessions)
    models = {
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=7, min_samples_leaf=10, random_state=42, n_jobs=2),
        "xgboost": XGBClassifier(n_estimators=250, max_depth=4, learning_rate=.04, subsample=.8,
                                  colsample_bytree=.8, objective="binary:logistic", eval_metric="logloss",
                                  random_state=42, n_jobs=2),
        "lightgbm": LGBMClassifier(n_estimators=250, num_leaves=15, learning_rate=.04,
                                   min_child_samples=20, random_state=42, verbosity=-1),
    }
    ytrain=(train_data["target_return_pct"]>0).astype(int)
    ycal=(cal_data["target_return_pct"]>0).astype(int)
    ytest=(test_data["target_return_pct"]>0).astype(int)
    if min(ytrain.nunique(),ycal.nunique(),ytest.nunique())<2:
        raise ValueError("class collapsed in one of the temporal partitions")
    report={"schema":"sky-ai-direction-training-audit-v1", "horizon":horizon,
            "features":list(feature_cols),"embargo_sessions":embargo_sessions,
            "splits":{"train_n":len(train_data),"calibration_n":len(cal_data),"oos_n":len(test_data),
                      "train_end":str(train_data["date"].max()),"calibration_end":str(cal_data["date"].max()),
                      "oos_end":str(test_data["date"].max())},
            "models":{},"production_eligible":False,"probabilities_verified":False,
            "note":"Research baseline only. Historical holdout metrics are NOT live calibration proof; no mobile probability publication without governance."}
    for name, estimator in models.items():
        estimator.fit(train_data[feature_cols], ytrain)
        cal_raw=estimator.predict_proba(cal_data[feature_cols])[:,1]
        test_raw=estimator.predict_proba(test_data[feature_cols])[:,1]
        from sklearn.linear_model import LogisticRegression
        calibrator=LogisticRegression(random_state=42)
        calibrator.fit(cal_raw.reshape(-1,1),ycal)
        test_cal=calibrator.predict_proba(test_raw.reshape(-1,1))[:,1]
        report["models"][name]={"uncalibrated_oos":metrics(ytest,test_raw),
                                "calibrated_oos":metrics(ytest,test_cal)}
    return report


def main():
    import pandas as pd
    from research.build_ml_dataset import FEATURE_COLS
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True)
    ap.add_argument("--horizon",choices=["intraday","next_day"],required=True)
    ap.add_argument("--embargo-sessions",type=int,required=True)
    ap.add_argument("--out",default="research_output/ai_direction_audit.json")
    args=ap.parse_args()
    path=Path(args.dataset)
    df=pd.read_parquet(path) if path.suffix==".parquet" else pd.read_csv(path)
    for field in ("date", "feature_available_at", "label_end_at"):
        if field not in df:
            raise ValueError("missing required causal timestamp " + field)
        df[field] = pd.to_datetime(df[field], utc=True, errors="raise")
    df=df.dropna(subset=FEATURE_COLS+["target_return_pct"])
    report=train(df,FEATURE_COLS,horizon=args.horizon,embargo_sessions=args.embargo_sessions)
    dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"RESEARCH_ONLY","out":str(dest),"models":list(report["models"])},ensure_ascii=False))


if __name__=="__main__":
    main()
