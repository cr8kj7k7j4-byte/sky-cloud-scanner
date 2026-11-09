"""Information-first 13-column Swing 5D observations; never trade authorization."""
from __future__ import annotations

COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
    "空方評分", "買進觸發", "最高接受價", "停損／失效",
    "現在動作", "加碼價格", "停利價格",
)


def build_swing5d_13col_rows(snapshot_observations, confirmations):
    """Show acquired evidence even when the market gate blocks strategy signals.

    Only independently corroborated fresh executed trades populate 即時價.
    Raw bulk prices remain available in separate provenance fields, never
    silently relabelled live. No unverified score or trade price is invented.
    """
    verified = {
        str(x.get("symbol")): x
        for x in confirmations
        if x.get("data_status") == "FRESH_EXECUTED_TRADE"
        and x.get("verified_executed_price") is not None
        and x.get("verified_executed_at")
    }
    output = []
    for item in snapshot_observations:
        symbol = str(item.get("symbol") or "")
        live = verified.get(symbol)
        row = {field: "待確認" for field in COLUMNS}
        row.update({
            "股票代碼": symbol,
            "股票名稱": item.get("name") or "待確認",
            "即時價": live["verified_executed_price"] if live else "待確認",
            "分類": "X",
            "方向": "不交易",
            "多方評分": "—",
            "空方評分": "—",
            "現在動作": "觀察" if live else "等待",
        })
        row["資料來源"] = (live or item).get("source") or "待確認"
        row["資料時間"] = live["verified_executed_at"] if live else "待確認"
        row["最近觀察價（未驗證成交時間）"] = item.get("indicative_last_price")
        row["資料狀態"] = ("個股成交價時間已複核；5D策略未驗證"
                       if live else "批量快照成交時間未驗證")
        row["研究狀態"] = "RESEARCH_ONLY_HOLD"
        row["正式交易資格"] = False
        output.append(row)
    return output


def render_swing5d_13col_table(rows, limit=20):
    lines = ["| " + " | ".join(COLUMNS) + " |",
             "| " + " | ".join("---" for _ in COLUMNS) + " |"]
    for row in rows[:limit]:
        cells = [str(row.get(col, "待確認")).replace("|", "/").replace("\n", " ")
                 for col in COLUMNS]
        lines.append("| " + " | ".join(cells) + " |")
    if not rows:
        cells = ["—", "暫無可驗證觀察", "待確認", "X", "不交易",
                 "—", "—", "待確認", "待確認", "待確認",
                 "等待", "待確認", "待確認"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
