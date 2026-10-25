import argparse
import json
from pathlib import Path

from src.historical_replay import ReplayPolicy, replay_universe


def load_objects(data_dir):
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
    ap.add_argument("--output",default="research_output/replay_dataset.jsonl")
    ap.add_argument("--summary",default="research_output/replay_summary.json")
    ap.add_argument("--horizon-bars",type=int,default=12)
    ap.add_argument("--cost-pct",type=float,default=0.45)
    ap.add_argument("--max-price",type=float,default=100.0)
    args=ap.parse_args()

    objects=load_objects(args.data_dir)
    result=replay_universe(
        objects,
        policy=ReplayPolicy(
            horizon_bars=args.horizon_bars,
            round_trip_cost_pct=args.cost_pct,
            max_price=args.max_price,
        ),
    )

    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as fh:
        for row in result["rows"]:
            fh.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")

    summary={
        k:v for k,v in result.items() if k!="rows"
    }
    Path(args.summary).write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
