"""Presentation-only 13-column Sky stock observation renderer.

Never converts a snapshot into an executable price or a research score into a
probability. Callers must supply sourced observations and provenance metadata.
"""
from __future__ import annotations

COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分", "空方評分",
    "買進觸發", "最高接受價", "停損／失效", "現在動作", "加碼價格", "停利價格",
)
MISSING = "待確認"
ACTIONS = frozenset(("買進", "等待", "觀察", "續抱", "加碼", "減碼", "停損", "退出", "禁止交易"))


def _cell(value, default=MISSING):
    if value is None or value == "":
        return default
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _score(value):
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not 0 <= number <= 100:
        return "—"
    return str(int(number)) if number.is_integer() else str(round(number, 1))


def render_sky_table(observations, *, source=None, observed_at=None,
                     trade_eligible=False, verified_executions=False):
    """Render all supplied observations; only use empty row for empty input.

    The caller must not mark verified_executions=True without independently
    checking per-symbol executed trade prices and timestamps.
    """
    header = "| " + " | ".join(COLUMNS) + " |"
    rule = "|" + "|".join("---" for _ in COLUMNS) + "|"
    lines = [header, rule]
    items = list(observations or [])
    for row in items:
        eligible = bool(trade_eligible and row.get("trade_eligible") is True)
        action = row.get("現在動作", "等待")
        if action not in ACTIONS:
            action = "等待"
        if not eligible and action in {"買進", "加碼"}:
            action = "禁止交易"
        price = row.get("即時價") if verified_executions and row.get("executed_trade_verified") is True else MISSING
        values = [
            _cell(row.get("股票代碼"), "—"),
            _cell(row.get("股票名稱")),
            _cell(price),
            _cell(row.get("分類"), "X"),
            _cell(row.get("方向"), "不交易"),
            _score(row.get("多方評分")),
            _score(row.get("空方評分")),
            _cell(row.get("買進觸發")),
            _cell(row.get("最高接受價")),
            _cell(row.get("停損／失效")),
            action,
            _cell(row.get("加碼價格")),
            _cell(row.get("停利價格")),
        ]
        lines.append("| " + " | ".join(values) + " |")
    if not items:
        lines.append("| — | 暫無合格候選 | 待確認 | X | 不交易 | — | — | 待確認 | 待確認 | 待確認 | 等待 | 待確認 | 待確認 |")
    state = "🟡 等待或觀察" if trade_eligible else "🔴 禁止新進場、未驗證通過"
    return "\n".join([
        state,
        f"資料來源：{_cell(source)}｜資料時間：{_cell(observed_at)}｜已驗證即時成交：{'是' if verified_executions else '否'}",
        *lines,
    ])
