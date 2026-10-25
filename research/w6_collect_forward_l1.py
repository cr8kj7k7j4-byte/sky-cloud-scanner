from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.w6_execution_evidence import (
    append_evidence_jsonl,
    paper_snapshot_to_w6_evidence,
)


def load_paper_records(root: str | Path) -> list[dict]:
    root = Path(root)
    records: list[dict] = []
    for path in sorted(root.rglob("*.json")):
        if "paper" not in {part.lower() for part in path.parts}:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("records") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            records.extend(x for x in rows if isinstance(x, dict))
    return records


def deduplicate(records: list[dict]) -> list[dict]:
    out = {}
    for row in records:
        key = (
            str(row.get("run_id") or ""),
            str(row.get("symbol") or ""),
            str(row.get("observation_timestamp") or row.get("observed_at") or ""),
        )
        out[key] = row
    return list(out.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-root", default="shadow_history")
    ap.add_argument("--evidence-out", default="research_output/w6_execution_evidence.jsonl")
    args = ap.parse_args()

    rows = deduplicate(load_paper_records(args.paper_root))
    out = Path(args.evidence_out)
    if out.exists():
        out.unlink()

    written = 0
    with_spread = 0
    for row in rows:
        evidence = paper_snapshot_to_w6_evidence(row)
        append_evidence_jsonl(evidence, out)
        written += 1
        if evidence.get("bid") is not None and evidence.get("ask") is not None:
            with_spread += 1

    print(json.dumps({
        "paper_records": len(rows),
        "evidence_rows": written,
        "rows_with_bid_ask": with_spread,
        "evidence_out": str(out),
        "note": (
            "Quote-only rows preserve fill_status=UNKNOWN. They support Spread "
            "research only and cannot establish Slippage/Fill/Adverse Selection."
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
