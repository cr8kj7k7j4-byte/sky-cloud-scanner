"""On-demand read-only ChatGPT bridge running inside GitHub Actions.

Only research observations are produced; no trade orders or model promotion.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUEST = Path("scan_requests/chat/latest.json")
OUTPUT = Path("output/chat_bridge")
COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
           "空方評分", "買進觸發", "最高接受價", "停損／失效",
           "現在動作", "加碼價格", "停利價格")


def validate_request(payload):
    if not isinstance(payload, dict) or payload.get("command") != "Sky 當沖現在掃一次":
        raise ValueError("UNSUPPORTED_COMMAND")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not (8 <= len(request_id) <= 80):
        raise ValueError("INVALID_REQUEST_ID")
    if not all(c.isascii() and (c.isalnum() or c in "-_") for c in request_id):
        raise ValueError("UNSAFE_REQUEST_ID")
    if payload.get("read_only_no_orders") is not True:
        raise ValueError("ORDER_POLICY_REQUIRED")
    return request_id


def validate_report(report):
    if report.get("schema") != "SKY_DAYTRADE_13COL_RESEARCH_V2":
        raise ValueError("INVALID_REPORT_SCHEMA")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != report.get("row_count"):
        raise ValueError("INCOMPLETE_ROWS")
    for row in rows:
        if not isinstance(row, dict) or any(k not in row for k in COLUMNS):
            raise ValueError("MISSING_13_COLUMNS")
    if report.get("production_eligible") is not False:
        raise ValueError("RESEARCH_CANNOT_AUTOPROMOTE")
    return rows


def make_status(request_id, report=None, error=None):
    run_id = os.getenv("GITHUB_RUN_ID") or "LOCAL"
    repo = os.getenv("GITHUB_REPOSITORY") or ""
    rows = validate_report(report) if report is not None else []
    return {
        "schema": "SKY_CHAT_SCAN_STATUS_V1",
        "request_id": request_id, "scan_id": run_id,
        "run_url": f"https://github.com/{repo}/actions/runs/{run_id}" if repo else None,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "REPORT_READY_RESEARCH_ONLY" if report is not None else "FAILED",
        "data_timestamp": report.get("checked_at_tpe") if report else None,
        "source": "FUGLE_PAID_SNAPSHOT" if report else None,
        "universe_count": report.get("universe_count") if report else None,
        "row_count": len(rows), "preview": rows[:8],
        "production_eligible": False, "automatic_order": False,
        "block_reason": error or "UNVERIFIED_EXECUTED_TRADE_COVERAGE",
        "artifact_file": "output/sky_quickscan_information/latest_13col.json" if report else None,
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    request_id = "INVALID"
    report = None
    error = None
    try:
        request_id = validate_request(json.loads(REQUEST.read_text(encoding="utf-8")))
        for argv in (
            [sys.executable, "-m", "research.sky_full_universe_information"],
            [sys.executable, "-m", "research.sky_13col_report",
             "--input", "output/sky_quickscan_information/full_universe.json",
             "--output", "output/sky_quickscan_information/latest_13col.md",
             "--json-output", "output/sky_quickscan_information/latest_13col.json"],
        ):
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=240, check=False)
            if proc.returncode != 0:
                raise RuntimeError(f"RUNNER_FAILED:{argv[2]}:EXIT_{proc.returncode}")
        report = json.loads(Path("output/sky_quickscan_information/latest_13col.json").read_text(encoding="utf-8"))
        validate_report(report)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        error = str(exc)[:160]
        report = None
    status = make_status(request_id, report, error)
    (OUTPUT / "latest.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "preview"}, ensure_ascii=False))
    if report is None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
