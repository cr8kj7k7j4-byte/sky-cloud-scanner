from __future__ import annotations

import argparse
import json

from research.w6_execution_evidence import load_evidence_jsonl, summarize_p1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="output/private/w6_execution_evidence.jsonl")
    ap.add_argument("--output")
    args = ap.parse_args()

    rows = load_evidence_jsonl(args.input)
    summary = summarize_p1(rows)
    payload = {
        "candidate": "P1_SPREAD_SLIPPAGE_BASELINE",
        "execution_type": "MIXED_OBSERVED_EXECUTION",
        "data_source": args.input,
        **summary,
        "status_w6": "EXECUTION_CANDIDATE" if summary["status"] == "P1_BASELINE_READY" else "INSUFFICIENT_DATA",
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
