from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.audit_trail import reconstructability_check
from src.decision_explainability import explain_decision

def load_jsonl(path):
    rows=[]
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--audit",required=True)
    ap.add_argument("--decision-id",required=True)
    ap.add_argument("--out",default="research_output/audit_replay.json")
    args=ap.parse_args()

    rows=load_jsonl(args.audit)
    match=next((x for x in rows if x.get("decision_id")==args.decision_id),None)
    if match is None:
        raise SystemExit("decision_id not found")

    report={
        "record":match,
        "reconstructability":reconstructability_check(match),
        "explanation":explain_decision(match),
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
