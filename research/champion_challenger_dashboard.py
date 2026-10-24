from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.champion_challenger import ShadowOutcome, compare_roles, compare_by_regime
from src.challenger_promotion_review import challenger_review


def load_jsonl(path):
    rows=[]
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",default="research_output/champion_challenger_dashboard.json")
    args=ap.parse_args()

    raw=load_jsonl(args.input)
    rows=[ShadowOutcome(**x) for x in raw]
    overall=compare_roles(rows)
    regimes=compare_by_regime(rows)
    review=challenger_review(overall,regime_comparisons=regimes)

    report={
        "overall":overall,
        "by_regime":regimes,
        "review":review,
        "live_order_allowed":False,
        "note":"Dashboard is shadow evidence only; no automatic promotion or live trading."
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
