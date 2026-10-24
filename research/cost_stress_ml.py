from __future__ import annotations
import argparse, json
from pathlib import Path

import joblib
import numpy as np

from research.build_ml_dataset import FEATURE_COLS
from research.train_ml_models import load_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="research_output/ml_dataset.csv")
    ap.add_argument("--model", default="research_output/models/xgboost.joblib")
    ap.add_argument("--out", default="research_output/cost_stress.json")
    ap.add_argument("--threshold-pct", type=float, default=0.5)
    ap.add_argument("--costs", default="0.30,0.45,0.60,0.80")
    args = ap.parse_args()

    df = load_dataset(args.dataset).dropna(subset=FEATURE_COLS + ["target_return_pct"]).copy()
    model = joblib.load(args.model)
    pred = model.predict(df[FEATURE_COLS])
    df["prediction"] = pred

    # Research-only long filter: only act when predicted return clears threshold.
    chosen = df[df["prediction"] >= args.threshold_pct].copy()
    costs = [float(x) for x in args.costs.split(",") if x.strip()]

    results = []
    for cost in costs:
        if chosen.empty:
            results.append({"cost_pct": cost, "n": 0, "expectancy_net_pct": None, "win_rate": None})
            continue
        net = chosen["target_return_pct"] - cost
        results.append({
            "cost_pct": cost,
            "n": int(len(net)),
            "expectancy_net_pct": float(net.mean()),
            "win_rate": float((net > 0).mean()),
        })

    passed = bool(results and all(
        r["n"] > 0 and r["expectancy_net_pct"] is not None and r["expectancy_net_pct"] > 0
        for r in results
    ))
    report = {
        "threshold_pct": args.threshold_pct,
        "results": results,
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "note": "Research-only cost stress; positive expectancy across tested costs is necessary but not sufficient for production.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
