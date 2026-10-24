from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def metrics(rows):
    xs = [num(r.get("net_r")) for r in rows]
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x < 0]
    gp = sum(wins)
    gl = -sum(losses)
    return {
        "n": len(xs),
        "win_rate": round(sum(x > 0 for x in xs) / len(xs), 4),
        "expectancy_r": round(statistics.mean(xs), 4),
        "pf": round(gp / gl, 4) if gl else None,
    }


def bucket(v):
    if v is None:
        return "UNKNOWN"
    if v >= 80:
        return "80_100"
    if v >= 60:
        return "60_79"
    if v >= 40:
        return "40_59"
    return "lt_40"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--out", default="research_output_stage6b/score_analysis.json")
    args = ap.parse_args()

    with Path(args.trades).open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    dimensions = [
        "event_score",
        "catalyst_score",
        "source_confidence_score",
        "freshness_score",
        "event_composite_score",
    ]

    report = {
        "scope": "Stage6B event-score post analysis",
        "all": metrics(rows),
        "dimensions": {},
        "by_year": {},
        "promotion_decision": "RESEARCH_ONLY",
        "notes": [
            "Scores are research features, not true probabilities.",
            "No promotion unless OOS/walk-forward/cost/leakage checks pass.",
        ],
    }

    for dim in dimensions:
        groups = defaultdict(list)
        for r in rows:
            groups[bucket(num(r.get(dim)))].append(r)
        report["dimensions"][dim] = {
            k: metrics(v) for k, v in sorted(groups.items())
        }

    by_year = defaultdict(list)
    for r in rows:
        d = str(r.get("action_date") or "")
        if len(d) >= 4:
            by_year[d[:4]].append(r)
    report["by_year"] = {y: metrics(v) for y, v in sorted(by_year.items())}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
