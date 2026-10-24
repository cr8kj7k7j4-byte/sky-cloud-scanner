import argparse
import json
from pathlib import Path

from src.training_dataset import build_training_dataset
from src.walk_forward import generate_walk_forward_folds
from src.walk_forward_eval import evaluate_walk_forward


def load_jsonl(path):
    rows=[]
    with Path(path).open("r",encoding="utf-8") as fh:
        for line in fh:
            line=line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="output/trade_decisions.jsonl")
    ap.add_argument("--output",default="output/ml_walk_forward_report.json")
    ap.add_argument("--start",required=True)
    ap.add_argument("--end",required=True)
    ap.add_argument("--train-days",type=int,default=504)
    ap.add_argument("--validate-days",type=int,default=126)
    ap.add_argument("--test-days",type=int,default=126)
    ap.add_argument("--step-days",type=int,default=126)
    args=ap.parse_args()

    records=load_jsonl(args.input)
    ds=build_training_dataset(records)
    folds=generate_walk_forward_folds(
        args.start,args.end,
        train_days=args.train_days,
        validate_days=args.validate_days,
        test_days=args.test_days,
        step_days=args.step_days,
    )
    report={
        "dataset":{
            "eligible_count":ds["eligible_count"],
            "rejected_count":ds["rejected_count"],
            "feature_keys":ds["feature_keys"],
        },
        "walk_forward":evaluate_walk_forward(
            ds["rows"],folds,ds["feature_keys"],target_key="r_multiple"
        ),
    }
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report["dataset"],ensure_ascii=False))


if __name__=="__main__":
    main()
