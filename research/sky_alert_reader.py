"""Fail-closed Sky 警戒 consumer for an EXISTING full-universe artifact.

This module does not fetch market data or trigger any scan. It only reads the
canonical research snapshot and refuses to describe stale observations as live.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Taipei")
SCHEMA = "SKY_ALERT_READ_RECEIPT_V1"
SOURCE_SCHEMA = "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1"
MAX_REPORT_AGE_SECONDS = 300
MAX_TRADE_AGE_SECONDS = 180


def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(TZ) if dt.tzinfo else None


def consume(report, *, now=None):
    now = (now or datetime.now(TZ)).astimezone(TZ)
    if not isinstance(report, dict) or report.get("schema") != SOURCE_SCHEMA:
        raise ValueError("INVALID_SOURCE_SCHEMA")
    if not isinstance(report.get("all_symbols"), list) or not isinstance(report.get("ranked_observations"), list):
        raise ValueError("INVALID_SOURCE_ROWS")
    # A zero-row artifact can be retained as evidence but must never be
    # reported as a current usable whole-market observation.
    if not report["all_symbols"]:
        raise ValueError("EMPTY_SOURCE_ROWS")
    checked = _timestamp(report.get("checked_at_tpe"))
    age = (now - checked).total_seconds() if checked else None
    if age is None:
        status = "MISSING_SOURCE_TIME"
    elif age < 0:
        status = "FUTURE_SOURCE_TIME"
    elif now.date() != checked.date() or age > MAX_REPORT_AGE_SECONDS:
        status = "STALE_SOURCE"
    else:
        status = "CURRENT_REPORT_OBSERVATION_ONLY"

    # Re-evaluate each row against the *reader's* clock. Original FRESH status
    # was only valid at generation, never indefinitely transferable to readers.
    rows = []
    for original in report["all_symbols"]:
        if not isinstance(original, dict):
            raise ValueError("INVALID_SOURCE_ROW")
        row = dict(original)
        trade_time = _timestamp(row.get("last_trade_time"))
        trade_age = (now - trade_time).total_seconds() if trade_time else None
        fresh = (
            status == "CURRENT_REPORT_OBSERVATION_ONLY"
            and row.get("data_status") == "FRESH_EXECUTED_TRADE"
            and trade_age is not None
            and trade_time.date() == now.date()
            and 0 <= trade_age <= MAX_TRADE_AGE_SECONDS
            and isinstance(row.get("last_price"), (int, float))
            and not isinstance(row.get("last_price"), bool)
            and math.isfinite(row["last_price"])
            and row["last_price"] > 0
        )
        if not fresh:
            row["data_status"] = "STALE_AT_READ" if trade_time else "UNVERIFIED_AT_READ"
        row["production_eligible"] = False
        row["trade_signal"] = False
        row.pop("required_fields", None)  # project display against fresh reader status
        rows.append(row)

    indexed = {(x.get("exchange"), str(x.get("symbol"))): x for x in rows}
    ranked = []
    for old in report["ranked_observations"]:
        if not isinstance(old, dict):
            raise ValueError("INVALID_RANKED_ROW")
        item = indexed.get((old.get("exchange"), str(old.get("symbol"))))
        if item is not None:
            ranked.append(item)

    output = dict(report)
    output["all_symbols"] = rows
    output["ranked_observations"] = ranked
    output["fresh_executed_count"] = sum(x.get("data_status") == "FRESH_EXECUTED_TRADE" for x in rows)
    output["fresh_executed_pct"] = round(100 * output["fresh_executed_count"] / len(rows), 1) if rows else 0.0
    output["by_exchange"] = {
        name: {**stats,
               "fresh_executed": sum(x.get("exchange") == name and x.get("data_status") == "FRESH_EXECUTED_TRADE" for x in rows),
               "fresh_executed_pct": round(100 * sum(x.get("exchange") == name and x.get("data_status") == "FRESH_EXECUTED_TRADE" for x in rows) / stats["universe"], 1) if stats.get("universe") else 0.0}
        for name, stats in (report.get("by_exchange") or {}).items()
    }
    output["trade_decision"] = "🔴 禁止新進場、未驗證通過"
    return {
        "schema": SCHEMA,
        "read_at_tpe": now.isoformat(),
        "source_checked_at_tpe": report.get("checked_at_tpe"),
        "source_age_seconds": round(age, 1) if age is not None else None,
        "freshness_status": status,
        "source_schema": SOURCE_SCHEMA,
        "observation_available": bool(rows),
        "fresh_executed_count_at_read": output["fresh_executed_count"],
        "production_eligible": False,
        "action": "禁止交易",
        "report": output,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Existing scan artifact; never an inferred latest run")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        receipt = consume(payload)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        receipt = {
            "schema": SCHEMA, "read_at_tpe": datetime.now(TZ).isoformat(),
            "freshness_status": "DATA_BLOCKED", "block_reason": str(exc),
            "observation_available": False, "production_eligible": False,
            "action": "禁止交易", "report": None,
        }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = "# Sky 警戒｜讀取及新鮮度驗證\n\n"
    md += f"讀取狀態：{receipt['freshness_status']}；讀取時間：{receipt['read_at_tpe']}\n\n"
    if receipt.get("report"):
        md += f"來源時間：{receipt['source_checked_at_tpe']}；距今秒數：{receipt['source_age_seconds']}\n\n"
        # Historical artifacts can predate fields required by the newer
        # full-universe presentation. A missing presentation field must never
        # prevent writing a fail-closed external readback receipt.
        report = receipt["report"]
        md += (
            f"觀察檔數：{len(report['all_symbols'])}；"
            f"讀取時有效逐筆成交檔數：{receipt['fresh_executed_count_at_read']}\n\n"
        )
        md += "歷史資料只能作為研究觀察，不代表即時行情或交易訊號。\n"
    else:
        md += f"資料讀取失敗：{receipt.get('block_reason', 'UNKNOWN')}\n"
    md += "\n**🔴 禁止新進場、未驗證通過；不得將過期觀察價視為即時成交價。**\n"
    args.markdown_output.write_text(md, encoding="utf-8")
    print(f"Sky alert reader: {receipt['freshness_status']}")
    if receipt["freshness_status"] != "CURRENT_REPORT_OBSERVATION_ONLY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
