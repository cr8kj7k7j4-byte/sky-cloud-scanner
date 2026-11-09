"""Evidence-first 13-column swing postmarket observation, never trade certification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .swing_observation_report import HEADERS, cell


def review_rows(scan: dict, full: dict | None = None) -> list[list]:
    observations = (full or {}).get("data")
    if observations is None:
        observations = scan.get("unverified_snapshot_observations") or []
    rows = []
    for item in observations:
        price = item.get("indicative_last_price")
        # A source snapshot is informative, not a verified executable live trade.
        price_display = f"{price}（未驗證快照）" if price is not None else "待確認"
        rows.append([
            item.get("symbol") or "—", item.get("name") or "待確認",
            price_display, "X／研究觀察", "待確認", "—", "—",
            "待確認", "待確認", "未驗證最近成交時間／策略資格",
            "觀察", "待確認", "待確認",
        ])
    if not rows:
        rows.append([
            "—", "暫無合格候選", "待確認", "X", "不交易", "—", "—",
            "待確認", "待確認", "待確認", "等待", "待確認", "待確認",
        ])
    return rows


def render(scan: dict, full: dict | None = None) -> str:
    lines = [
        "🔴 禁止新進場、未驗證通過；觀察資訊仍照實展示。",
        "",
        "# Sky 盤後複盤｜波段（研究觀察，非已實現績效）",
        "",
        f"掃描資料時間：{cell(scan.get('generated_at'))}；來源：Fugle bulk snapshot（觀察層）",
        f"市場涵蓋範圍：TWSE＋TPEx；快照涵蓋率：{cell(scan.get('snapshot_coverage_pct'))}% "
        f"；認證即時成交覆蓋率：{cell(scan.get('quote_coverage_pct'))}%",
        f"完整觀察筆數：{cell((full or {}).get('observed_symbols') if full else scan.get('unverified_snapshot_observation_count'))}；"
        f"本表列出：{len(review_rows(scan, full)) if (full or {}).get('data') or scan.get('unverified_snapshot_observations') else 0}",
        "快照價可能已過期，缺少逐股實際成交時間；「即時價」欄以「未驗證快照」標示，並非認證即時價。",
        "未取得可核對的歷史建議、真實成交與成本資料時，不計算勝率、R 倍數或淨損益。",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    lines.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in review_rows(scan, full))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/swing_live/latest_swing.json")
    parser.add_argument("--full", default="output/swing_live/snapshot_observations_swing.json")
    parser.add_argument("--output", default="output/swing_live/latest_swing_postmarket_13_columns.md")
    args = parser.parse_args()
    input_path = Path(args.input)
    scan = json.loads(input_path.read_text(encoding="utf-8")) if input_path.is_file() else {
        "warnings": ["SWING_SCAN_MISSING"], "generated_at": None
    }
    full_path = Path(args.full)
    full = json.loads(full_path.read_text(encoding="utf-8")) if full_path.is_file() else None
    result = render(scan, full)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    print(result[:1600])
    import os
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as f:
            f.write("\n" + result[:20000] + "\n")


if __name__ == "__main__":
    main()
