from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_INPUTS = {
    "decision_stream":"research_data/intraday_pit/decisions.csv",
    "pit_intervals":"research_data/intraday_pit/pit_intervals.json",
    "market_context":"research_data/intraday_pit/market_context.csv",
    "sector_context":"research_data/intraday_pit/sector_context.csv",
    "feature_context":"research_data/intraday_pit/feature_context.csv",
    "ranking_context":"research_data/intraday_pit/ranking_context.csv",
    "execution_context":"research_data/intraday_pit/execution_context.csv",
    "outcomes":"research_data/intraday_pit/outcomes.csv",
}

def inspect(root: str=".") -> dict:
    base=Path(root)
    inputs={}
    for key,rel in REQUIRED_INPUTS.items():
        p=base/rel
        inputs[key]={"path":rel,"exists":p.exists(),"bytes":p.stat().st_size if p.exists() else 0}
    missing=[k for k,v in inputs.items() if not v["exists"] or v["bytes"]==0]
    blockers=[]
    if missing:
        blockers.append("MISSING_PROMOTION_GRADE_INPUTS:"+",".join(missing))
    if not inputs["sector_context"]["exists"]:
        blockers.append("NO_EFFECTIVE_DATED_HISTORICAL_SECTOR_MAPPING")
    if not inputs["decision_stream"]["exists"]:
        blockers.append("NO_CANONICAL_HISTORICAL_DECISION_STREAM")
    if not inputs["outcomes"]["exists"]:
        blockers.append("NO_CANONICAL_OUTCOME_JOIN_INPUT")
    return {
        "issue":81,
        "status":"READY_TO_BUILD" if not blockers else "DATA_BLOCKED",
        "inputs":inputs,
        "blockers":blockers,
        "highest_priority_blocker":blockers[0] if blockers else None,
        "note":"Repository readiness inventory only. A PASS here does not replace coverage/leakage/timestamp/W2 contract audits.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--out",default="research_output/intraday_pit_replay/readiness.json")
    args=ap.parse_args()
    report=inspect(args.root)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
