from __future__ import annotations
import argparse, json
from pathlib import Path

import joblib
import pandas as pd
import shap

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--model", default="research_output/models/xgboost.joblib")
    ap.add_argument("--out", default="research_output/shap_summary.json")
    ap.add_argument("--sample", type=int, default=500)
    args = ap.parse_args()

    df = load_dataset(args.dataset).dropna(subset=FEATURE_COLS)
    sample = df.tail(args.sample)
    model = joblib.load(args.model)

    explainer = shap.TreeExplainer(model)
    values = explainer(sample[FEATURE_COLS])
    importance = abs(values.values).mean(axis=0)

    ranked = sorted(
        [
            {"feature": feature, "mean_abs_shap": float(score)}
            for feature, score in zip(FEATURE_COLS, importance)
        ],
        key=lambda x: x["mean_abs_shap"],
        reverse=True,
    )

    report = {
        "method": "TreeSHAP",
        "sample_n": len(sample),
        "feature_importance": ranked,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
