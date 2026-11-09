"""Read-only Sky pre-open and intraday data delivery watchdog.

Does not claim market-data certification, create orders or modify trading rules.
Historical last-known report is allowed overnight but never labelled live.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
FIELDS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
          "空方評分", "買進觸發", "最高接受價", "停損／失效",
          "現在動作", "加碼價格", "停利價格")
INPUT = Path("docs/SKY_UNIFIED_LATEST_ALL_MARKET.json")
OUTPUT = Path("output/sky_recovery_watchdog/latest.json")


def audit(status, now):
    now_tpe = now.astimezone(TZ)
    minutes = now_tpe.hour * 60 + now_tpe.minute
    # During market hours, freshness should be checked only AFTER the first
    # scan has had a reasonable window to finish. Overnight old data is fine
    # as historical evidence, but NEVER a fresh signal.
    active = now_tpe.weekday() < 5 and 9 * 60 + 15 <= minutes < 13 * 60 + 30
    pub = status.get("published_at_utc")
    age_minutes = None
    try:
        stamp = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
        if stamp.tzinfo is not None:
            age_minutes = round((now - stamp.astimezone(timezone.utc)).total_seconds()/60, 1)
    except (ValueError, TypeError):
        pass
    swing = (status.get("reports") or {}).get("swing5d_research") or {}
    actual = tuple(swing.get("information_columns_13col") or ())
    count = swing.get("information_count_13col")
    has_format = actual == FIELDS
    has_rows = isinstance(count, int) and count > 0
    fresh = age_minutes is not None and -2 <= age_minutes <= 25
    verdict = ("BLOCKED_NO_13_COLUMNS" if not has_format
               else "BLOCKED_MISSING_OBSERVATIONS" if not has_rows
               else "BLOCKED_STALE_SCAN" if active and not fresh
               else "REPORT_AVAILABLE_HISTORICAL_ONLY" if not active
               else "REPORT_AVAILABLE_MARKET_DATA_UNCERTIFIED")
    return {
        "schema": "SKY_RECOVERY_WATCHDOG_V1",
        "checked_at_tpe": now_tpe.isoformat(),
        "active_market_session": active,
        "last_report_at_utc": pub,
        "last_report_age_minutes": age_minutes,
        "source_run_url": status.get("run_url"),
        "report_13_columns_valid": has_format,
        "information_row_count": count,
        "has_observations": has_rows,
        "report_fresh_for_market_session": fresh if active else False,
        "whole_market_live_trade_certified": bool(
            swing.get("operational_full_market_scan") is True),
        "strategy_production_eligible": False,
        "action": "禁止交易",
        "verdict": verdict,
        "errors": ([] if has_format else ["MISSING_13_COLUMN_REPORT"]) +
                  ([] if has_rows else ["MISSING_OR_ZERO_INFORMATION_ROWS"]) +
                  ([] if not active or fresh else ["STALE_INTRADAY_REPORT"]),
        "note": "Health only. No automatic orders, no Alpha changes, no claim of verified live whole-market execution.",
    }


def main():
    try:
        source = json.loads(INPUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        source = {}
    now = datetime.now(timezone.utc)
    report = audit(source, now)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## Sky Watchdog\n\n")
            for key in ("checked_at_tpe", "verdict", "information_row_count",
                        "source_run_url", "report_fresh_for_market_session",
                        "whole_market_live_trade_certified"):
                fh.write(f"- {key}: {report.get(key)}\n")
    print(json.dumps(report, ensure_ascii=False))
    if report["verdict"].startswith("BLOCKED_"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
