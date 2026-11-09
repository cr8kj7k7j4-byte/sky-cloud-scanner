"""Render Sky research observations in the user's 13-column mobile contract.

This is a read-only formatter, NOT an AI prediction engine. Never call a
snapshot price "live" without FRESH_EXECUTED_TRADE evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
           "空方評分", "買進觸發", "最高接受價", "停損／失效",
           "現在動作", "加碼價格", "停利價格")
UNKNOWN = "待確認"


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _cell(value):
    return str(value if value not in (None, "") else UNKNOWN).replace("|", "／").replace("\n", " ")


def projection(item):
    """All unavailable strategy fields remain unknown, never inferred."""
    verified = item.get("data_status") == "FRESH_EXECUTED_TRADE"
    price = _number(item.get("last_price")) if verified else None
    # Data quality X is not a model's directional recommendation.
    row = dict.fromkeys(COLUMNS, UNKNOWN)
    row.update({
        "股票代碼": item.get("symbol") or "—",
        "股票名稱": item.get("name") or UNKNOWN,
        "即時價": f"{price:.2f}" if price is not None else UNKNOWN,
        "分類": "X",
        "方向": "不交易",
        "多方評分": "—",
        "空方評分": "—",
        "現在動作": "等待",
    })
    return row


def render(report, *, limit=30):
    if not isinstance(report, dict) or report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("unsupported_source_schema")
    if not isinstance(report.get("all_symbols"), list):
        raise ValueError("all_symbols_missing")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("invalid_limit")
    rows = report["all_symbols"]
    # Prefer ranked observations for the first screen, but keep the full source
    # in the underlying JSON. Do not imply ranked rows are trade candidates.
    ranked = report.get("ranked_observations")
    if isinstance(ranked, list) and ranked:
        rows = ranked
    lines = [
        "# Sky｜13 欄市場研究資訊（非隔日預測）",
        "",
        f"資料查詢時間：{_cell(report.get('checked_at_tpe'))}",
        f"母池：{report.get('universe_count', UNKNOWN)}；已觀察價格：{report.get('observed_price_count', UNKNOWN)}；"
        f"新鮮成交驗證：{report.get('fresh_executed_count', UNKNOWN)}",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "| " + " | ".join("---" for _ in COLUMNS) + " |",
    ]
    for item in rows[:limit]:
        if not isinstance(item, dict):
            continue
        projected = projection(item)
        lines.append("| " + " | ".join(_cell(projected[col]) for col in COLUMNS) + " |")
    if len(lines) == 6:
        fallback = {"股票代碼": "—", "股票名稱": "暫無合格候選", "分類": "X",
                    "方向": "不交易", "多方評分": "—", "空方評分": "—",
                    "現在動作": "等待"}
        lines.append("| " + " | ".join(_cell(fallback.get(col)) for col in COLUMNS) + " |")
    lines += ["", "未驗證的報價、分數、觸發、停損與停利一律不補造。",
              "非新鮮成交的最近觀察價仍保留於來源 JSON（last_price、data_status、last_trade_time），"
              "不得冒充即時價。", "",
              "**🔴 禁止新進場、未驗證通過。資訊供自主判斷，並非正式交易訊號。**"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("output/sky_quickscan_information/full_universe.json"))
    parser.add_argument("--output", type=Path, default=Path("output/sky_quickscan_information/latest_13col.md"))
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    rendered = render(report, limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Rendered {args.output} (research only)")


if __name__ == "__main__":
    main()
