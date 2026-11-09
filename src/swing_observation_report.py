"""Evidence-first 13-column mobile swing observation report.

Do not transform research candidates into production trades or invent entry levels.
"""
from __future__ import annotations
import json
from pathlib import Path

HEADERS = [
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
    "空方評分", "買進觸發", "最高接受價", "停損／失效",
    "現在動作", "加碼價格", "停利價格",
]


def cell(value):
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "／").replace("\n", " ")


def observation_rows(report):
    result = []
    for c in report.get("candidates", []):
        price = c.get("current_price") if c.get("live_quote_status") == "FRESH_DATE_AND_TIMESTAMP_VERIFIED" else None
        result.append([
            c.get("symbol"), c.get("name"), price,
            c.get("classification") or "研究觀察／未評級",
            c.get("direction") or "待確認",
            c.get("bull_score"), c.get("bear_score"),
            c.get("buy_trigger"), c.get("highest_acceptable_price"),
            c.get("invalidation_text") or "正式模型訊號未驗證",
            "觀察", c.get("add_price"), c.get("target_price"),
        ])
    return result


def render(report):
    rows = observation_rows(report)
    out = [
        "## Sky 波段研究觀察｜13 欄完整呈現（非正式交易訊號）", "",
        f"產出時間：{cell(report.get('generated_at'))}；官方日線訊號日：{cell(report.get('official_daily_signal_date'))}",
        f"上市＋上櫃前日收盤：{cell(report.get('official_daily_count'))}/{cell(report.get('universe_count'))}（{cell(report.get('official_daily_coverage_pct'))}%）",
        f"富果候選當日成交價：{cell(report.get('live_quote_available'))}/{cell(report.get('live_quote_requested'))}；全市場盤中即時覆蓋率：未驗證",
        f"資料狀態：{cell(report.get('daily_scope_status'))}；研究資格：NOT_PRODUCTION",
        "🔴 未通過正式進場資格仍展示全部已取得的研究觀察，使用者自行決定交易；不得自動下單。",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    for r in rows:
        out.append("| " + " | ".join(cell(v) for v in r) + " |")
    if not rows:
        out.append("| " + " | ".join(["無候選"] + ["—"] * (len(HEADERS)-2) + ["觀察"]) + " |")
    out += [
        "",
        "—＝尚無可追溯的正式計算依據，不是零分或零價格；研究觀察未評級不等於 A 或 A+。",
        "現價僅為候選股已驗證的富果成交快照，不保證閱讀當下仍即時；每檔原始報價時間詳見 JSON。",
        "前日收盤覆蓋率不是全市場即時成交價覆蓋率；日線研究篩選不是 V1.1 買進觸發。",
        "",
        "### 候選股逐檔資料證據",
    ]
    for c in report.get("candidates", []):
        out.append(
            f"- {cell(c.get('symbol'))} {cell(c.get('name'))}：前收盤 {cell(c.get('close'))}；"
            f"當日成交快照 {cell(c.get('current_price'))}；成交時間 {cell(c.get('current_price_updated_at'))}；"
            f"來源 {cell(c.get('current_price_source'))}；前日成交量 {cell(c.get('volume_lots'))} 張；"
            f"狀態 {cell(c.get('live_quote_status'))}；未確認：日週線觸發、停損、停利、成本後 RR。"
        )
    return "\n".join(out) + "\n"


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8")) if source.is_file() else {
        "candidates": [], "daily_scope_status": "DATA_BLOCKED"
    }
    text = render(report)
    output = Path("output/swing_split_scope/latest_13_columns.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
