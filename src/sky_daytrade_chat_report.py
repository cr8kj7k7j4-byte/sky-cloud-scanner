"""Safe, read-only 13-column chat projection of Sky full-market observations.

Consumes a completed scanner artifact. It NEVER requests quotes, invokes models,
authorizes orders, or turns an observed (possibly stale) price into a live quote.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分", "空方評分",
    "買進觸發", "最高接受價", "停損／失效", "現在動作", "加碼價格", "停利價格",
)
DISPLAY_MISSING = "—"
FRESH = "FRESH_EXECUTED_TRADE"


def _value(value):
    return DISPLAY_MISSING if value is None or value == "" else str(value)


def project(report: dict, limit: int = 30) -> dict:
    """Map source-attributed observations to the user's exact 13 columns.

    No guessed levels: this informational artifact does not carry governed
    setup/trigger/model scores. The model and trade gate stay independent.
    """
    if not isinstance(report, dict) or report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("Unsupported report schema; never infer market data")
    if limit < 0:
        raise ValueError("limit must be nonnegative")
    observations = report.get("ranked_observations") or []
    rows = []
    for item in observations[:limit]:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue
        fresh = item.get("data_status") == FRESH
        rows.append({
            "股票代碼": _value(item.get("symbol")),
            "股票名稱": _value(item.get("name")),
            "即時價": _value(item.get("last_price")) if fresh else DISPLAY_MISSING,
            "分類": "X",
            "方向": "待確認",
            "多方評分": DISPLAY_MISSING,
            "空方評分": DISPLAY_MISSING,
            "買進觸發": DISPLAY_MISSING,
            "最高接受價": DISPLAY_MISSING,
            "停損／失效": DISPLAY_MISSING,
            "現在動作": "禁止交易",
            "加碼價格": DISPLAY_MISSING,
            "停利價格": DISPLAY_MISSING,
            "資料時間": item.get("last_trade_time"),
            "資料來源": item.get("source"),
            "觀察價（未必即時）": item.get("last_price"),
            "當日成交量（來源未完全驗證）": item.get("volume"),
            "資料狀態": item.get("data_status"),
        })
    return {
        "schema": "SKY_DAYTRADE_CHAT_13_COLUMNS_V1",
        "command": "Sky 當沖現在掃一次",
        "report_checked_at_tpe": report.get("checked_at_tpe"),
        "universe_count": report.get("universe_count"),
        "observed_price_count": report.get("observed_price_count"),
        "fresh_executed_count": report.get("fresh_executed_count"),
        "fresh_executed_pct": report.get("fresh_executed_pct"),
        "by_exchange": report.get("by_exchange"),
        "snapshot_errors": report.get("snapshot_errors"),
        "data_mode": "INFORMATION_OBSERVATION_NOT_FULL_MARKET_VERIFIED_LIVE",
        "model_executed": False,
        "production_eligible": False,
        "action": "禁止交易",
        "columns": list(COLUMNS),
        "rows": rows,
        "limitation": "觀察價不是即時價；未連接獨立驗證模型與交易觸發，所有訊號欄位不得臆測。",
    }


def markdown(view: dict) -> str:
    cols = view["columns"]
    out = [
        "# Sky 當沖｜13欄觀察報告（非交易訊號）",
        f"資料檢查時間：{_value(view.get('report_checked_at_tpe'))}",
        f"母池：{_value(view.get('universe_count'))}；有觀察價：{_value(view.get('observed_price_count'))}；驗證新鮮成交：{_value(view.get('fresh_executed_count'))}；比例：{_value(view.get('fresh_executed_pct'))}%",
        "模型未執行；行情完整性未通過；禁止交易。未驗證價格不放入即時價欄。",
        "",
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in view["rows"]:
        out.append("| " + " | ".join(_value(row.get(col)).replace("|", "／") for col in cols) + " |")
    if not view["rows"]:
        out.append("目前沒有可展示的觀察名單；不能宣稱全市場沒有合格標的。")
    out += [
        "",
        "附註：每檔來源、資料時間、觀察價及資料狀態詳見同目錄 JSON 的 rows；缺少即時成交證據一律不顯示即時價。",
        "**🔴 禁止新進場／未驗證通過。**",
    ]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render existing Sky observation artifact for ChatGPT")
    parser.add_argument("--input", default="output/sky_quickscan_information/full_universe.json")
    parser.add_argument("--out-dir", default="output/sky_daytrade_chat")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    view = project(report, limit=args.limit)
    target = Path(args.out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "latest.json").write_text(json.dumps(view, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "latest.md").write_text(markdown(view), encoding="utf-8")


if __name__ == "__main__":
    main()
