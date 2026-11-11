"""Fail-closed Sky 警戒 consumer for an EXISTING full-universe artifact.

This module does not fetch market data or trigger any scan. It only reads the
canonical research snapshot and refuses to describe stale observations as live.
"""
from __future__ import annotations

import argparse
import hashlib
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
    declared_count = report.get("universe_count")
    if type(declared_count) is not int or declared_count != len(report["all_symbols"]):
        raise ValueError("UNIVERSE_COUNT_MISMATCH")
    # A file with duplicated identifiers can fake market coverage. Validate
    # both listed exchanges against the advertised canonical source counts.
    keys = []
    for entry in report["all_symbols"]:
        if not isinstance(entry, dict) or entry.get("exchange") not in ("TWSE", "TPEx"):
            raise ValueError("INVALID_SOURCE_ROW")
        symbol = str(entry.get("symbol") or "")
        if not symbol:
            raise ValueError("MISSING_SOURCE_SYMBOL")
        keys.append((entry["exchange"], symbol))
    if len(set(keys)) != len(keys):
        raise ValueError("DUPLICATE_SOURCE_SYMBOLS")
    exchange_counts = report.get("by_exchange")
    if not isinstance(exchange_counts, dict) or not all(
        isinstance(exchange_counts.get(market), dict)
        and type(exchange_counts[market].get("universe")) is int
        and exchange_counts[market]["universe"] ==
        sum(entry["exchange"] == market for entry in report["all_symbols"])
        for market in ("TWSE", "TPEx")
    ):
        raise ValueError("EXCHANGE_COVERAGE_MISMATCH")
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
    # Source clock freshness is not the same as a verified executed trade.
    # Preserve all information rows, but do not advertise a zero-trade
    # snapshot as a current usable market observation.
    if status == "CURRENT_REPORT_OBSERVATION_ONLY" and output["fresh_executed_count"] == 0:
        status = "NO_VERIFIED_EXECUTIONS"
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


def receipt_report_sha256(report):
    """Canonical digest of report bytes represented in the published JSON.

    A digest detects accidental post-publication receipt/report corruption.
    It is not a signature and cannot authenticate an untrusted artifact.
    """
    return hashlib.sha256(json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def consume_uploaded_receipt(payload, *, expected_run_id, expected_head_sha, now=None):
    """Consume an externally downloaded scan.yml readback receipt, without network access.

    Bind the ZIP receipt to an explicitly selected GitHub run and commit.
    Re-evaluate the original source rows at *this* reader's clock; a previously
    fresh receipt cannot become a permanently fresh mobile command response.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("INVALID_UPLOADED_RECEIPT_SCHEMA")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("schema") != "SKY_ALERT_EXTERNAL_READBACK_PROVENANCE_V1":
        raise ValueError("MISSING_UPLOADED_PROVENANCE")
    if (not isinstance(expected_run_id, str) or not expected_run_id.isdigit()
            or not isinstance(expected_head_sha, str) or len(expected_head_sha) != 40
            or any(ch not in "0123456789abcdef" for ch in expected_head_sha.lower())):
        raise ValueError("INVALID_EXPECTED_SOURCE_ID")
    if str(provenance.get("source_run_id")) != expected_run_id:
        raise ValueError("UPLOADED_RUN_ID_MISMATCH")
    if provenance.get("source_head_sha") != expected_head_sha:
        raise ValueError("UPLOADED_HEAD_SHA_MISMATCH")
    if provenance.get("source_repo") != "cr8kj7k7j4-byte/sky-cloud-scanner":
        raise ValueError("UPLOADED_REPOSITORY_MISMATCH")
    if provenance.get("source_artifact") != "sky-scan-" + expected_run_id:
        raise ValueError("UPLOADED_ARTIFACT_MISMATCH")
    if provenance.get("download_outcome") != "success" or not provenance.get("input_sha256"):
        raise ValueError("UPLOADED_DOWNLOAD_NOT_VERIFIED")
    if provenance.get("production_eligible") is not False or payload.get("production_eligible") is not False:
        raise ValueError("UPLOADED_RESEARCH_GUARD_FAILED")
    source_report = payload.get("report")
    if not isinstance(source_report, dict):
        raise ValueError("UPLOADED_REPORT_MISSING")
    digest = provenance.get("receipt_report_sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or digest != receipt_report_sha256(source_report)):
        raise ValueError("UPLOADED_REPORT_HASH_MISMATCH")
    result = consume(source_report, now=now)
    result["provenance"] = dict(provenance)
    result["provenance_validated_at_read"] = True
    result["external_mobile_command_verified"] = False
    result["production_eligible"] = False
    result["action"] = "禁止交易"
    return result


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Existing full-universe source artifact")
    source.add_argument("--receipt", type=Path, help="Previously downloaded sky-alert-readback JSON")
    parser.add_argument("--expected-run-id", help="Required when consuming a downloaded receipt")
    parser.add_argument("--expected-head-sha", help="Required when consuming a downloaded receipt")
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads((args.input or args.receipt).read_text(encoding="utf-8"))
        if args.receipt:
            receipt = consume_uploaded_receipt(
                payload, expected_run_id=args.expected_run_id,
                expected_head_sha=args.expected_head_sha,
            )
        else:
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
