"""Render Sky research observations in the user's 13-column mobile contract.

This is a read-only formatter, NOT an AI prediction engine. Never call a
snapshot price "live" without FRESH_EXECUTED_TRADE evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from research.sky_daytrade_evidence_bridge import observation_evidence, scanner_plans

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


def projection(item, plan=None):
    """All unavailable strategy fields remain unknown, never inferred."""
    verified = item.get("data_status") == "FRESH_EXECUTED_TRADE"
    price = _number(item.get("last_price")) if verified else None
    observed = _number(item.get("last_price"))
    # A same-session paid Fugle observation is visible but NOT a live trade.
    show_observed = (
        not verified and observed is not None
        and item.get("source") == "Fugle paid bulk snapshot"
        and item.get("data_status") in ("UNVERIFIED_EXECUTION_TIME", "STALE_EXECUTION_TIME")
    )
    # Data quality X is not a model's directional recommendation.
    row = dict.fromkeys(COLUMNS, UNKNOWN)
    row.update({
        "股票代碼": item.get("symbol") or "—",
        "股票名稱": item.get("name") or UNKNOWN,
        "即時價": (f"{price:.2f}" if price is not None else
                    f"待確認（觀察價 {observed:.2f}，未驗證）" if show_observed else UNKNOWN),
        "分類": "X",
        "方向": "不交易",
        "多方評分": "—",
        "空方評分": "—",
        "現在動作": "等待",
    })
    evidence = observation_evidence(item)
    if evidence.get("bull") is not None and evidence.get("bear") is not None:
        row["多方評分"] = evidence["bull"]
        row["空方評分"] = evidence["bear"]
        row["方向"] = str(evidence.get("direction") or "觀察") + "（研究）"
    if isinstance(plan, dict):
        row["買進觸發"] = f"{plan['trigger']:.2f}（研究）"
        row["最高接受價"] = f"{plan['max_entry']:.2f}（研究）"
        row["停損／失效"] = f"{plan['stop']:.2f}（研究）"
        row["停利價格"] = f"{plan['target']:.2f}（研究）"
    return row


def render(report, *, limit=0, scanner=None):
    if not isinstance(report, dict) or report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("unsupported_source_schema")
    if not isinstance(report.get("all_symbols"), list):
        raise ValueError("all_symbols_missing")
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("invalid_limit")
    rows = report["all_symbols"]
    ranked = report.get("ranked_observations")
    if isinstance(ranked, list) and ranked:
        ordered, seen = [], set()
        for item in ranked + rows:
            if not isinstance(item, dict):
                continue
            key = (item.get("exchange"), item.get("symbol"))
            if key not in seen:
                seen.add(key)
                ordered.append(item)
        rows = ordered
    plans = scanner_plans(scanner)
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
    for item in (rows[:limit] if limit else rows):
        if not isinstance(item, dict):
            continue
        projected = projection(item, plans.get(str(item.get('symbol') or '')))
        lines.append("| " + " | ".join(_cell(projected[col]) for col in COLUMNS) + " |")
    if not rows:
        fallback = {"股票代碼": "—", "股票名稱": "暫無合格候選", "分類": "X",
                    "方向": "不交易", "多方評分": "—", "空方評分": "—",
                    "現在動作": "等待"}
        lines.append("| " + " | ".join(_cell(fallback.get(col)) for col in COLUMNS) + " |")
    lines += ["", "研究多空分數只依同日富果價量證據計算，非勝率；標示（研究）的點位只來自同輪掃描既有的策略計畫。",
              "非新鮮成交的最近觀察價仍保留於來源 JSON（last_price、data_status、last_trade_time），"
              "不得冒充即時價。", "",
              "**🔴 禁止新進場、未驗證通過。資訊供自主判斷，並非正式交易訊號。**"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("output/sky_quickscan_information/full_universe.json"))
    parser.add_argument("--output", type=Path, default=Path("output/sky_quickscan_information/latest_13col.md"))
    parser.add_argument("--limit", type=int, default=0, help="0 exports all symbols; positive values are previews")
    parser.add_argument("--scanner-input", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    scanner = (json.loads(args.scanner_input.read_text(encoding="utf-8"))
               if args.scanner_input and args.scanner_input.is_file() else None)
    rendered = render(report, limit=args.limit, scanner=scanner)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    if args.json_output:
        rows = report["all_symbols"]
        if args.limit:
            rows = rows[:args.limit]
        plans = scanner_plans(scanner)
        projected = []
        for item in rows:
            row = projection(item, plans.get(str(item.get("symbol") or "")))
            row["資料來源"] = item.get("source")
            row["資料時間"] = item.get("last_trade_time")
            row["資料狀態"] = item.get("data_status")
            row["研究分數狀態"] = observation_evidence(item).get("status")
            row["正式交易資格"] = False
            projected.append(row)
        payload = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                   "checked_at_tpe": report.get("checked_at_tpe"),
                   "universe_count": report.get("universe_count"),
                   "row_count": len(projected), "rows": projected,
                   "production_eligible": False}
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    print(f"Rendered {args.output} (research only)")


if __name__ == "__main__":
    main()
