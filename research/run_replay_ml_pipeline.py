import argparse
import json
from pathlib import Path

from src.historical_replay import ReplayPolicy, replay_universe
from src.training_dataset import build_training_dataset
from src.walk_forward import generate_walk_forward_folds
from src.walk_forward_eval import evaluate_walk_forward


def _load_objects(data_dir):
    objects=[]
    for path in sorted(Path(data_dir).glob("*_5.json")):
        if path.name.startswith("_"):
            continue
        try:
            objects.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return objects


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",default="research_data/history")
    ap.add_argument("--out-dir",default="research_output/pipeline")
    ap.add_argument("--start",required=True)
    ap.add_argument("--end",required=True)
    ap.add_argument("--horizon-bars",type=int,default=12)
    ap.add_argument("--cost-pct",type=float,default=0.45)
    ap.add_argument("--max-price",type=float,default=100.0)
    ap.add_argument("--train-days",type=int,default=504)
    ap.add_argument("--validate-days",type=int,default=126)
    ap.add_argument("--test-days",type=int,default=126)
    ap.add_argument("--step-days",type=int,default=126)
    args=ap.parse_args()

    out_dir=Path(args.out_dir)
    out_dir.mkdir(parents=True,exist_ok=True)

    objects=_load_objects(args.data_dir)
    replay=replay_universe(
        objects,
        policy=ReplayPolicy(
            horizon_bars=args.horizon_bars,
            round_trip_cost_pct=args.cost_pct,
            max_price=args.max_price,
        ),
    )

    replay_path=out_dir/"replay_dataset.jsonl"
    with replay_path.open("w",encoding="utf-8") as fh:
        for row in replay["rows"]:
            fh.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")

    dataset=build_training_dataset(replay["rows"])
    folds=generate_walk_forward_folds(
        args.start,args.end,
        train_days=args.train_days,
        validate_days=args.validate_days,
        test_days=args.test_days,
        step_days=args.step_days,
    )
    report=evaluate_walk_forward(
        dataset["rows"],folds,dataset["feature_keys"],target_key="r_multiple"
    )

    summary={
        "source_files":len(objects),
        "replay_rows":replay["count"],
        "training_rows":dataset["eligible_count"],
        "training_rejected":dataset["rejected_count"],
        "feature_keys":dataset["feature_keys"],
        "fold_count":len(folds),
        "walk_forward":report,
        "production_eligible":False,
        "promotion_status":"RESEARCH_ONLY",
        "limitations":replay["limitations"] + [
            "No production promotion occurs from this pipeline automatically.",
            "Historical data coverage and survivorship bias must be reviewed before interpreting model metrics.",
        ],
    }
    (out_dir/"pipeline_report.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "source_files":summary["source_files"],
        "replay_rows":summary["replay_rows"],
        "training_rows":summary["training_rows"],
        "fold_count":summary["fold_count"],
        "production_eligible":False,
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
