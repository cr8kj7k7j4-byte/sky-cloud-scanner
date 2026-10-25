from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.model_registry import build_shadow_promotion_dashboard
from src.shadow_evidence import (
    evaluate_shadow_pipeline_readiness,
    evaluate_portfolio_cost_capacity_evidence,
)


def load_shadow_records(root):
    root = Path(root)
    records = []
    files = sorted(
        path for path in root.rglob("*.json")
        if "paper" in {part.lower() for part in path.parts}
    )
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("records") if isinstance(payload, dict) else None
        if isinstance(rows, list):
            records.extend(x for x in rows if isinstance(x, dict))
    dedup = {}
    for row in records:
        key = (
            str(row.get("run_id") or ""),
            str(row.get("symbol") or ""),
            str(row.get("observed_at") or ""),
        )
        current = dedup.get(key)
        if current is None:
            dedup[key] = row
            continue

        current_outcome = dict(current.get("outcome") or {})
        new_outcome = dict(row.get("outcome") or {})
        current_rank = dict(current_outcome.get("ranking") or {})
        new_rank = dict(new_outcome.get("ranking") or {})

        current_score = (
            2 if current_rank.get("status") == "COMPLETE"
            else 1 if current_outcome.get("status") == "COMPLETE"
            else 0
        )
        new_score = (
            2 if new_rank.get("status") == "COMPLETE"
            else 1 if new_outcome.get("status") == "COMPLETE"
            else 0
        )
        if new_score > current_score:
            dedup[key] = row

    return list(dedup.values()), files


def load_json(path):
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def build_w4_report_sections(dashboard):
    """Canonical W4 report surface. Descriptive evidence only."""
    s = dict(dashboard.get("summary") or {})
    gaps = dict(dashboard.get("sample_gaps") or {})
    portfolio = dict(dashboard.get("portfolio_cost_capacity") or {})
    observed = dict(portfolio.get("observed") or {})
    pipeline = dict(dashboard.get("pipeline_readiness") or {})
    sample_suff = dict(dashboard.get("sample_sufficiency") or {})

    stage = dashboard.get("stage") or "WAITING_FOR_FUTURE_SAMPLE"
    drift_status = (
        "WAITING_FOR_FUTURE_SAMPLE"
        if stage == "WAITING_FOR_FUTURE_SAMPLE"
        else "NOT_YET_BREACHED"
    )
    return {
        "Sample Progress": {
            "status": stage,
            "samples": s.get("samples", 0),
            "trading_days": s.get("trading_days", 0),
            "regime_count": s.get("regime_count", 0),
        },
        "Data Completeness": {
            "pipeline_status": pipeline.get("status", "UNKNOWN"),
            "outcome_complete_ratio": s.get("outcome_complete_ratio", 0),
            "sample_gate_sufficient": bool(sample_suff.get("sufficient", False)),
        },
        "Strategy Performance": {
            "expectancy_r": observed.get("expectancy_r"),
            "profit_factor": observed.get("profit_factor"),
            "max_drawdown_r": observed.get("max_drawdown_r"),
            "note": "Counterfactual/Shadow evidence only; not realized trading PnL.",
        },
        "Risk": {
            "portfolio_status": portfolio.get("status", "NOT_EVALUABLE"),
            "top_symbol_share": s.get("top_symbol_share", 0),
            "cost_complete_ratio": observed.get("cost_complete_ratio", 0),
            "production_eligible": False,
        },
        "Drift": {
            "status": drift_status,
            "note": (
                "Requires sufficient forward evidence before Backtest vs Shadow/"
                "Paper/Live deterioration can be interpreted."
            ),
        },
        "Promotion Readiness": {
            "status": stage,
            "promotable_to_governance_review": bool(
                s.get("promotable_to_governance_review", False)
            ),
            "production_eligible": False,
            "blocking_items": list(dashboard.get("blocking_items") or []),
        },
        "Outstanding Days / Samples": {
            "samples_remaining": gaps.get("samples_remaining", 0),
            "trading_days_remaining": gaps.get("trading_days_remaining", 0),
            "regimes_remaining": gaps.get("regimes_remaining", 0),
            "outcome_completeness_gap": gaps.get("outcome_completeness_gap", 0),
            "symbol_concentration_excess": gaps.get("symbol_concentration_excess", 0),
        },
    }


def render_markdown(dashboard):
    report = build_w4_report_sections(dashboard)
    lines = [
        "# W4｜Sky Shadow / Paper / Live Evidence",
        "",
        f"**Status:** {dashboard.get('stage')}",
        "",
    ]
    for title, values in report.items():
        lines.append(f"## {title}")
        for key, value in values.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.append(
        "> Shadow/Paper 結果屬 forward/counterfactual evidence，不代表實際成交、"
        "真實損益、勝率或 Production 授權。"
    )
    return "\n".join(lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-dir", default="output/paper")
    ap.add_argument("--promotion-evidence")
    ap.add_argument("--artifact-type", default="RANKING")
    ap.add_argument(
        "--out",
        default="research_output/shadow_promotion_dashboard.json",
    )
    ap.add_argument(
        "--markdown-out",
        default="research_output/shadow_promotion_dashboard.md",
    )
    ap.add_argument("--min-samples", type=int, default=200)
    ap.add_argument("--min-trading-days", type=int, default=20)
    ap.add_argument("--min-regimes", type=int, default=2)
    ap.add_argument("--min-outcome-complete-ratio", type=float, default=0.95)
    ap.add_argument("--max-symbol-share", type=float, default=0.20)
    ap.add_argument("--min-expectancy-r", type=float, default=0.0)
    ap.add_argument("--min-profit-factor", type=float, default=1.0)
    ap.add_argument("--max-drawdown-r", type=float)
    ap.add_argument("--ledger-start", default="2026-10-24T23:28:08Z")
    ap.add_argument("--eligible-successful-scan-runs", type=int, default=0)
    ap.add_argument("--max-participation-rate", type=float)
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
    pipeline = evaluate_shadow_pipeline_readiness(
        ledger_start=args.ledger_start,
        eligible_successful_scan_runs=args.eligible_successful_scan_runs,
        paper_files=len(files),
        records_loaded=len(records),
    )
    portfolio = evaluate_portfolio_cost_capacity_evidence(
        records,
        max_participation_rate=args.max_participation_rate,
    )

    dashboard["source"] = {
        "paper_dir": str(args.paper_dir),
        "files_scanned": len(files),
        "records_loaded": len(records),
        "promotion_evidence_file": args.promotion_evidence,
    }
    dashboard["pipeline_readiness"] = pipeline
    dashboard["portfolio_cost_capacity"] = portfolio
    dashboard["w4_report"] = build_w4_report_sections(dashboard)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(dashboard), encoding="utf-8")
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
