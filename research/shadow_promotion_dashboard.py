from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.model_registry import build_shadow_promotion_dashboard


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


def render_markdown(dashboard):
    s = dashboard.get("summary", {})
    gaps = dashboard.get("sample_gaps", {})
    blockers = dashboard.get("blocking_items", [])
    source = dashboard.get("source", {})
    lines = [
        "# Sky Shadow Promotion Dashboard",
        "",
        f"**Stage:** {dashboard.get('stage')}",
        "",
        "| 指標 | 現況 |",
        "|---|---:|",
        f"| Shadow/Paper 樣本 | {s.get('samples', 0)} |",
        f"| 交易日 | {s.get('trading_days', 0)} |",
        f"| Regime 數 | {s.get('regime_count', 0)} |",
        f"| Outcome 完整率 | {float(s.get('outcome_complete_ratio', 0))*100:.1f}% |",
        f"| 單一股票最高占比 | {float(s.get('top_symbol_share', 0))*100:.1f}% |",
        f"| Promotion Evidence Score | {s.get('promotion_score', 0)} / 100 |",
        "",
        "## 樣本缺口",
        f"- 尚缺樣本：{gaps.get('samples_remaining', 0)}",
        f"- 尚缺交易日：{gaps.get('trading_days_remaining', 0)}",
        f"- 尚缺 Regime：{gaps.get('regimes_remaining', 0)}",
        f"- Outcome 完整率缺口：{float(gaps.get('outcome_completeness_gap', 0))*100:.1f} 個百分點",
        f"- 集中度超標：{float(gaps.get('symbol_concentration_excess', 0))*100:.1f} 個百分點",
        "",
        "## 阻塞項目",
    ]
    lines.extend([f"- {x}" for x in blockers] or ["- 無"])
    lines += [
        "",
        "## 資料來源",
        f"- 掃描 artifact 檔案數：{source.get('files_scanned', 0)}",
        f"- 載入 records：{source.get('records_loaded', 0)}",
        "",
        "> 此分數是升版證據成熟度，不是勝率、獲利機率或自動 Production 授權。",
    ]
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
    markdown_out = Path(args.markdown_out)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.write_text(render_markdown(dashboard), encoding="utf-8")
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
