from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.model_registry import build_shadow_promotion_dashboard


def load_shadow_records(root):
    root = Path(root)
    records = []
    files = sorted(root.glob("*.json"))
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("records") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            records.extend(x for x in rows if isinstance(x, dict))
    return records, files


def load_json(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-dir", default="output/paper")
    ap.add_argument("--promotion-evidence")
    ap.add_argument("--artifact-type", default="RANKING")
    ap.add_argument(
        "--out",
        default="research_output/shadow_promotion_dashboard.json",
    )
    ap.add_argument("--min-samples", type=int, default=200)
    ap.add_argument("--min-trading-days", type=int, default=20)
    ap.add_argument("--min-regimes", type=int, default=2)
    ap.add_argument("--min-outcome-complete-ratio", type=float, default=0.95)
    ap.add_argument("--max-symbol-share", type=float, default=0.20)
    ap.add_argument("--min-expectancy-r", type=float, default=0.0)
    ap.add_argument("--min-profit-factor", type=float, default=1.0)
    ap.add_argument("--max-drawdown-r", type=float)
    args = ap.parse_args()

    records, files = load_shadow_records(args.paper_dir)
    evidence = load_json(args.promotion_evidence)

    dashboard = build_shadow_promotion_dashboard(
        records,
        promotion_evidence=evidence,
        artifact_type=args.artifact_type,
        min_samples=args.min_samples,
        min_trading_days=args.min_trading_days,
        min_regimes=args.min_regimes,
        min_outcome_complete_ratio=args.min_outcome_complete_ratio,
        max_symbol_share=args.max_symbol_share,
        min_expectancy_r=args.min_expectancy_r,
        min_profit_factor=args.min_profit_factor,
        max_drawdown_r=args.max_drawdown_r,
    )
    dashboard["source"] = {
        "paper_dir": str(args.paper_dir),
        "files_scanned": len(files),
        "records_loaded": len(records),
        "promotion_evidence_file": args.promotion_evidence,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
