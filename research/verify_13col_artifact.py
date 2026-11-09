"""Verify read-only 13-column report matches a real scanner source artifact.

Designed for the workflow_run report after the scanner completes (even when the
executed-trade gate fails). This checks report integrity, not trade eligibility.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from research.sky_13col_report import COLUMNS


def validate(source, report, markdown):
    if source.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("SOURCE_SCHEMA_INVALID")
    originals = source.get("all_symbols")
    if not isinstance(originals, list) or not originals:
        raise ValueError("SOURCE_UNIVERSE_EMPTY")
    rows = report.get("rows")
    if not isinstance(rows, list) or report.get("schema") != "SKY_DAYTRADE_13COL_RESEARCH_V2":
        raise ValueError("OUTPUT_SCHEMA_INVALID")
    if len(rows) != len(originals) or report.get("row_count") != len(originals):
        raise ValueError("INCOMPLETE_13COL_UNIVERSE")
    if source.get("universe_count") != len(originals):
        raise ValueError("SOURCE_UNIVERSE_COUNT_MISMATCH")
    if report.get("universe_count") != len(originals):
        raise ValueError("REPORT_UNIVERSE_COUNT_MISMATCH")
    original_keys = [(str(row.get("exchange")), str(row.get("symbol"))) for row in originals]
    if len(original_keys) != len(set(original_keys)):
        raise ValueError("DUPLICATED_SOURCE_SYMBOLS")
    seen = set()
    allowed_actions = {"買進", "等待", "觀察", "續抱", "加碼", "減碼", "停損", "退出", "禁止交易"}
    for row, original in zip(rows, originals):
        if not isinstance(row, dict) or any(k not in row for k in COLUMNS):
            raise ValueError("13_COLUMNS_MISSING")
        symbol = str(row.get("股票代碼"))
        key = (str(original.get("exchange")), symbol)
        if symbol != str(original.get("symbol")) or key in seen:
            raise ValueError("REPORT_SYMBOL_ORDER_OR_DUPLICATE")
        seen.add(key)
        if original.get("source") not in ("Fugle paid bulk snapshot", "NO_SNAPSHOT_ROW"):
            raise ValueError("FREE_OR_UNRECOGNIZED_MARKETDATA_SOURCE")
        if row.get("資料來源") != original.get("source") or row.get("資料狀態") != original.get("data_status"):
            raise ValueError("DATA_SOURCE_STATUS_MISMATCH")
        if row.get("正式交易資格") is not False:
            raise ValueError("RESEARCH_PROMOTED_TO_TRADING")
        if row.get("現在動作") not in allowed_actions:
            raise ValueError("INVALID_ACTION")
        for name in ("多方評分", "空方評分"):
            value = row.get(name)
            if value not in ("—", "待確認", None):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
                    raise ValueError("INVALID_EVIDENCE_SCORE")
        if original.get("data_status") != "FRESH_EXECUTED_TRADE" and row.get("即時價", "").replace("待確認", "").strip() and "未驗證" not in row["即時價"]:
            raise ValueError("UNVERIFIED_PRICE_LABEL_MISSING")

    if report.get("production_eligible") is not False:
        raise ValueError("PRODUCTION_ELIGIBILITY_UNSAFE")
    if report.get("checked_at_tpe") != source.get("checked_at_tpe"):
        raise ValueError("REPORT_SOURCE_TIME_MISMATCH")
    table = [line for line in markdown.splitlines()
             if line.startswith("| ") and line.count("|") == len(COLUMNS) + 1]
    if not table or table[0] != "| " + " | ".join(COLUMNS) + " |":
        raise ValueError("MD_HEADER_MISSING_OR_INCORRECT")
    # Header plus separator plus all source rows.
    if len(table) != len(originals) + 2:
        raise ValueError("MARKDOWN_ROW_COUNT_MISMATCH")
    return {"source_count": len(originals), "json_rows": len(rows),
            "markdown_rows": len(table) - 2, "research_only": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    opts = parser.parse_args()
    result = validate(
        json.loads(opts.source.read_text(encoding="utf-8")),
        json.loads(opts.json.read_text(encoding="utf-8")),
        opts.markdown.read_text(encoding="utf-8"),
    )
    print("SKY_13COL_INTEGRITY_PASS", json.dumps(result))


if __name__ == "__main__":
    main()
