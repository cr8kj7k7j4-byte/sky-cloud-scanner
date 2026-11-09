"""Fail-closed contract for future ChatGPT -> Sky scan bridge.

This does NOT expose a network endpoint or grant MCP permissions. No trading actions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

COLUMNS_13 = (
    "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
    "空方評分", "買進觸發", "最高接受價", "停損／失效",
    "現在動作", "加碼價格", "停利價格",
)
ALLOWED_ACTIONS = frozenset(("買進", "等待", "觀察", "續抱", "加碼",
                             "減碼", "停損", "退出", "禁止交易"))


def validate_scan_result(payload: dict[str, Any], *, expected_scan_id: str) -> dict[str, Any]:
    """Validate provenance and shape; NEVER manufacture missing data."""
    if not isinstance(payload, dict) or not expected_scan_id:
        raise ValueError("INVALID_SCAN_INPUT")
    if payload.get("scan_id") != expected_scan_id:
        raise ValueError("SCAN_ID_MISMATCH_OR_STALE_CACHE")
    if payload.get("source") != "FUGLE":
        raise ValueError("NON_FUGLE_MARKET_DATA")
    if payload.get("automatic_order") is not False:
        raise ValueError("ORDER_PERMISSION_NOT_ALLOWED")
    stamped = payload.get("data_timestamp")
    try:
        observation_time = datetime.fromisoformat(stamped)
    except (TypeError, ValueError) as exc:
        raise ValueError("DATA_TIMESTAMP_MISSING_OR_INVALID") from exc
    if observation_time.tzinfo is None:
        raise ValueError("DATA_TIMESTAMP_MUST_INCLUDE_TIMEZONE")
    if observation_time.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise ValueError("DATA_TIMESTAMP_IN_FUTURE")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("ROWS_MISSING")
    for row in rows:
        if not isinstance(row, dict) or any(col not in row for col in COLUMNS_13):
            raise ValueError("INCOMPLETE_13_COLUMN_ROW")
        if row["現在動作"] not in ALLOWED_ACTIONS:
            raise ValueError("INVALID_ACTION")
    for key in ("universe_count", "verified_quote_count", "coverage_pct",
                "production_eligible", "block_reason", "run_url"):
        if key not in payload:
            raise ValueError(f"MISSING_{key.upper()}")
    if payload["production_eligible"] is not True:
        if any(row["現在動作"] in ("買進", "加碼") for row in rows):
            raise ValueError("BLOCKED_REPORT_CANNOT_RECOMMEND_ENTRY")
    if payload["verified_quote_count"] > payload["universe_count"]:
        raise ValueError("INVALID_QUOTE_COVERAGE")
    return payload
