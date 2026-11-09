"""Fail-closed integrity verification of independent paid-Fugle scan artifacts."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from research.sky_fugle_independent_scan import COLUMNS

DIRECTORY = Path("output/sky_fugle_independent")


def verify(source, report, markdown):
    if source.get("schema") != "SKY_FUGLE_INDEPENDENT_MARKET_SCAN_V1":
        raise ValueError("UNKNOWN_SOURCE_SCHEMA")
    if report.get("schema") != "SKY_FUGLE_INDEPENDENT_13COL_V1":
        raise ValueError("UNKNOWN_REPORT_SCHEMA")
    if report.get("columns") != list(COLUMNS):
        raise ValueError("INVALID_COLUMNS")
    if source.get("production_eligible") is not False or report.get("production_eligible") is not False:
        raise ValueError("UNSAFE_TRADE_PERMISSION")
    all_symbols = source.get("all_symbols")
    rows = report.get("rows")
    if not isinstance(all_symbols, list) or not isinstance(rows, list):
        raise ValueError("MISSING_ROWS")
    n = source.get("universe_count")
    if not isinstance(n, int) or n <= 0 or len(all_symbols) != n or len(rows) != n:
        raise ValueError("TRUNCATED_UNIVERSE")
    if source.get("checked_at_tpe") != report.get("checked_at_tpe"):
        raise ValueError("TIME_MISMATCH")
    symbols, observed, fresh = set(), 0, 0
    by_exchange = Counter()
    for item, row in zip(all_symbols, rows):
        key = (item.get("exchange"), item.get("symbol"))
        if key in symbols:
            raise ValueError("DUPLICATE_MARKET_SYMBOL")
        symbols.add(key)
        by_exchange[item.get("exchange")] += 1
        if item.get("symbol") != row.get("股票代碼") or item.get("name") != row.get("股票名稱") and item.get("name"):
            raise ValueError("ROW_ORDER_OR_NAME_MISMATCH")
        if any(field not in row for field in COLUMNS):
            raise ValueError("INCOMPLETE_13_FIELDS")
        if row.get("資料來源") != item.get("source") or row.get("資料時間") != item.get("last_trade_time"):
            raise ValueError("PROVENANCE_MISMATCH")
        if row.get("資料狀態") != item.get("data_status") or row.get("正式交易資格") is not False:
            raise ValueError("RESEARCH_PROMOTED_TO_TRADE")
        if row.get("現在動作") != "禁止交易":
            raise ValueError("INVALID_ACTION")
        if row.get("多方評分") != "—" or row.get("空方評分") != "—":
            raise ValueError("UNAUTHORIZED_MODEL_SCORE")
        if item.get("last_price") is not None:
            observed += 1
        if item.get("data_status") == "FRESH_EXECUTED_TRADE":
            fresh += 1
            if not item.get("last_trade_time"):
                raise ValueError("FRESH_WITHOUT_TRADE_TIME")
        elif item.get("last_price") is not None and "未驗證" not in str(row.get("即時價")):
            raise ValueError("OBSERVATION_MASQUERADES_AS_LIVE")
    if observed != source.get("observed_price_count") or fresh != source.get("fresh_executed_count"):
        raise ValueError("INVALID_COVERAGE_COUNTS")
    if any(by_exchange[x] != source.get("by_exchange", {}).get(x, {}).get("universe") for x in ("TWSE", "TPEx")):
        raise ValueError("EXCHANGE_UNIVERSE_MISMATCH")
    comparison = source.get("universe_comparison") or {}
    missing = comparison.get("official_not_in_fugle") or []
    if len(missing) != comparison.get("official_universe", -1) - (
        comparison.get("fugle_universe", -1) - len(comparison.get("fugle_not_in_official") or [])
    ):
        raise ValueError("UNIVERSE_DIFFERENCE_MISMATCH")
    if any((x.get("exchange"), x.get("symbol")) not in symbols for x in missing):
        raise ValueError("MISSING_OFFICIAL_SYMBOL_IN_REPORT")
    header = "| " + " | ".join(COLUMNS) + " |"
    if header not in markdown.splitlines():
        raise ValueError("INVALID_MARKDOWN_HEADER")
    if sum(1 for line in markdown.splitlines() if line.startswith("| ") and
           line.count("|") == len(COLUMNS) + 1) != n + 2:
        raise ValueError("TRUNCATED_MARKDOWN_REPORT")
    return {"status": "PASS", "official_universe": n,
            "priced_observations": observed, "verified_executed": fresh,
            "missing_paid_symbols": len(missing), "by_exchange": dict(by_exchange),
            "trade_permission": "NO_TRADE"}


def main():
    source = json.loads((DIRECTORY / "full_universe.json").read_text(encoding="utf-8"))
    report = json.loads((DIRECTORY / "latest_13col.json").read_text(encoding="utf-8"))
    markdown = (DIRECTORY / "latest_13col.md").read_text(encoding="utf-8")
    result = verify(source, report, markdown)
    (DIRECTORY / "integrity_receipt.json").write_text(json.dumps(
        result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SKY_INDEPENDENT_13COL_INTEGRITY_PASS", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
