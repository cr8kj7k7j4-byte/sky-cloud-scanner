"""Display verified research observations in the user's fixed 13-column view.

A display report is never a trade authorization and never fills missing values
from previous close, approximations, model proxies, or invented prices.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

COLUMNS = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向",
    "多方評分", "空方評分", "買進觸發", "最高接受價",
    "停損／失效", "現在動作", "加碼價格", "停利價格",
)

MISSING = "待確認"


def _display(value):
    if value is None or value == "" or isinstance(value, bool):
        return MISSING
    return str(value).replace("|", "｜").replace("\n", " ")


def render(report: dict) -> dict:
    if not isinstance(report, dict):
        raise ValueError("Research signal evidence must be an object")
    records = report.get("records") or []
    if not isinstance(records, list):
        raise ValueError("Research records must be an array")
    rows = []
    for record in records:
        if not isinstance(record, dict) or not record.get("symbol"):
            continue
        # Raw values remain available in the JSON evidence; only a quote with
        # per-symbol verified execution provenance can occupy the 'live' column.
        validated_quote = (
            record.get("status") == "RESEARCH_OBSERVATION"
            and record.get("reference_executed_price") is not None
            and record.get("quote_date")
            and record.get("quote_time")
        )
        value = _display(record.get("reference_executed_price")) if validated_quote else MISSING
        direction = _display(record.get("direction")) if validated_quote else "不交易"
        rows.append([
            _display(record.get("symbol")), _display(record.get("name")),
            value, "X", direction, "—", "—",
            MISSING, MISSING, MISSING, "觀察",
            MISSING, MISSING,
        ])
    if not rows:
        rows = [["—", "暫無合格候選", MISSING, "X", "不交易", "—", "—",
                 MISSING, MISSING, MISSING, "等待", MISSING, MISSING]]
    text = [
        "🔴 禁止新進場、未驗證通過｜研究觀察不等於交易資格",
        "",
        f"來源掃描 Run ID：{_display(report.get('source_run_id'))}",
        f"資料時間：{_display(report.get('scan_time'))}",
        f"行情來源：{_display(report.get('source_quote_provider'))}",
        f"市場資料閘門：{_display(report.get('market_data_gate'))}",
        f"研究訊號記錄：{len(records)}；具證據的模型 ID：{', '.join(report.get('observed_model_ids') or []) or '無'}",
        "注意：本表不是六套已驗證模型的宣告；研究分數不等於勝率。",
        "",
        "| " + " | ".join(COLUMNS) + " |",
        "| " + " | ".join([":---:"] * len(COLUMNS)) + " |",
    ]
    text += ["| " + " | ".join(row) + " |" for row in rows]
    text.append("")
    return {
        "schema": "SKY_SIX_MODEL_RESEARCH_DISPLAY_13_V1",
        "source_run_id": report.get("source_run_id"),
        "source_scan_time": report.get("scan_time"),
        "market_data_gate": report.get("market_data_gate"),
        "columns": list(COLUMNS), "rows": rows,
        "records_observed": len(records),
        "observed_model_ids": report.get("observed_model_ids") or [],
        "production_eligible": False, "live_order_enabled": False,
        "conclusion": "禁止新進場、未驗證通過",
        "markdown": "\n".join(text) + "\n",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", default="output/research_signals/latest_13col.json")
    parser.add_argument("--markdown", default="output/research_signals/latest_13col.md")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = render(source)
    for path, data in ((Path(args.out), json.dumps(output, ensure_ascii=False, indent=2) + "\n"),
                       (Path(args.markdown), output["markdown"])):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
    print(json.dumps({"rows": len(output["rows"]),
                      "observed": output["records_observed"],
                      "source_run_id": output["source_run_id"],
                      "production_eligible": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
