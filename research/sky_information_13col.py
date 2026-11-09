"""Render every available Sky observation in the requested 13-column format.

Information only: never converts a snapshot into a confirmed live execution,
a model score, a trading signal, or an entry/exit price.
"""
from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path("output/sky_quickscan_information/full_universe.json")
DEST = Path("output/sky_quickscan_information")
COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向",
    "多方評分", "空方評分", "買進觸發", "最高接受價",
    "停損／失效", "現在動作", "加碼價格", "停利價格",
)
FRESH = "FRESH_EXECUTED_TRADE"


def clean(value):
    return str(value if value is not None else "待確認").replace("|", "／").replace("\n", " ")


def quote_display(row):
    price = row.get("last_price")
    if price is None:
        return "待確認"
    try:
        observed = f"{float(price):.2f}"
    except (TypeError, ValueError, OverflowError):
        return "待確認"
    if row.get("data_status") == FRESH:
        return observed
    return f"觀察價 {observed}（未驗證）"


def render_row(row):
    required = row.get("required_fields") or {}
    fresh = row.get("data_status") == FRESH
    # Trade fields may only be used when separately verified by the decision
    # engine; this informational feed never infers them from price movement.
    return {
        "股票代碼": clean(row.get("symbol")),
        "股票名稱": clean(row.get("name")),
        "即時價": quote_display(row),
        "分類": "X",
        "方向": "不交易",
        "多方評分": "—",
        "空方評分": "—",
        "買進觸發": "待確認",
        "最高接受價": "待確認",
        "停損／失效": "待確認",
        "現在動作": "禁止交易",
        "加碼價格": "待確認",
        "停利價格": "待確認",
        "資料時間": row.get("last_trade_time"),
        "資料狀態": row.get("data_status") or "待確認",
        "資料來源": row.get("source") or "待確認",
        "交易資格": False,
        "最近觀察價": row.get("last_price"),
        "原始必要欄位": required,
        "已驗證即時成交": fresh,
    }


def build(payload):
    rows = [render_row(x) for x in payload.get("all_symbols", []) if isinstance(x, dict)]
    if not rows:
        rows = [render_row({"symbol": "—", "name": "暫無合格候選"})]
        rows[0]["現在動作"] = "等待"
    return {
        "schema": "SKY_INFORMATION_13_COLUMNS_V1",
        "checked_at_tpe": payload.get("checked_at_tpe"),
        "columns": list(COLUMNS),
        "universe_count": payload.get("universe_count"),
        "observed_price_count": payload.get("observed_price_count"),
        "fresh_executed_count": payload.get("fresh_executed_count"),
        "decision": "🔴 禁止新進場、未驗證通過",
        "production_eligible": False,
        "note": "即時價欄的觀察價不是經驗證的即時成交；無推論證據不填評分或交易價。",
        "rows": rows,
    }


def markdown(view, rows):
    lines = [
        "# Sky 全市場資訊｜13 欄固定格式",
        "",
        f"資料時間：{view.get('checked_at_tpe') or '待確認'}",
        f"母池：{view.get('universe_count') or '待確認'}；觀察價格：{view.get('observed_price_count') or 0}；驗證即時成交：{view.get('fresh_executed_count') or 0}",
        "注意：即時價欄標為「觀察價」者，不能視為即時成交價格。",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "| " + " | ".join("---" for _ in COLUMNS) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(k)) for k in COLUMNS) + " |")
    lines.extend(["", f"**{view['decision']}**", "資訊照常提供；實際交易由使用者自行決定。"])
    return "\n".join(lines) + "\n"


def main():
    # Fail visibly if upstream data was never created; do not fabricate market data.
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    view = build(payload)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "latest_13col.json").write_text(
        json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DEST / "latest_13col.md").write_text(
        markdown(view, view["rows"]), encoding="utf-8")
    (DEST / "latest_13col_preview.md").write_text(
        markdown(view, view["rows"][:30]), encoding="utf-8")
    print(f"SKY_13COL rows={len(view['rows'])} verified={view['fresh_executed_count']} action=NO_TRADE")


if __name__ == "__main__":
    main()
