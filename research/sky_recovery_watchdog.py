"""Read-only Sky watchdog. Records evidence, never changes trade eligibility.

The job runs every five minutes. Existing scan.yml owns all live data collection.
No automatic Production changes, orders or retry storms.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")
REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "output" / "sky_recovery_watchdog"
COLUMNS = ("股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
           "空方評分", "買進觸發", "最高接受價", "停損／失效",
           "現在動作", "加碼價格", "停利價格")

def read_json(path):
    try:
        return json.loads((REPO / path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

def check_contract():
    from src.sky_command_router import route_command
    from research.sky_full_universe_information import ALERT_COLUMNS, build, summary
    route = route_command("Sky 警戒")
    errors = []
    if route.command_family != "SKY_ALERT_WHOLE_MARKET_OBSERVATION":
        errors.append("ALERT_COMMAND_UNROUTED")
    if tuple(ALERT_COLUMNS) != COLUMNS:
        errors.append("ALERT_COLUMNS_NOT_13")
    sample = build(
        [{"symbol": "1234", "name": "測試", "exchange": "TWSE"}],
        {"TSE": {"date": "2026-11-09", "data": [
            {"symbol": "1234", "lastPrice": 50.5, "tradeVolume": 1000}
        ]}},
        datetime(2026, 11, 9, 11, 30, tzinfo=TPE),
    )
    table = summary(sample)
    if "1234 | 測試 | 待確認（觀察價 50.50，未驗證）" not in table:
        errors.append("UNVERIFIED_INFORMATION_HIDDEN")
    if sample["fresh_executed_count"] != 0:
        errors.append("UNVERIFIED_PRICE_PROMOTED")
    table_rows = [line for line in table.splitlines() if line.startswith("| 1234")]
    if len(table_rows) != 1 or len(table_rows[0].split("|")) - 2 != 13:
        errors.append("ALERT_TABLE_NOT_13_COLUMNS")
    return errors

def collect(now=None):
    now = now or datetime.now(TPE)
    errors = check_contract()
    market = read_json("docs/SKY_MCR_INTRADAY_HEALTH_LATEST.json") or {}
    unified = read_json("docs/SKY_UNIFIED_LATEST_ALL_MARKET.json") or {}
    observed = market.get("all_market_observed_price_count")
    universe = market.get("all_market_universe_count")
    fresh = market.get("all_market_fresh_executed_count")
    published = market.get("published_at_utc")
    report_age = None
    if published:
        try:
            stamp = datetime.fromisoformat(published.replace("Z", "+00:00"))
            report_age = round((now.astimezone(timezone.utc) - stamp).total_seconds())
        except (ValueError, TypeError):
            errors.append("INVALID_MARKET_REPORT_TIME")
    weekday_session = now.weekday() < 5 and (9 <= now.hour < 13 or
                       (now.hour == 13 and now.minute <= 30))
    recent = report_age is not None and -30 <= report_age <= 900
    market_status = ("DATA_BLOCKED_UNVERIFIED_EXECUTION" if fresh == 0 else
                     "PARTIAL_EXECUTION_ONLY" if isinstance(fresh, int) and fresh > 0 else
                     "UNKNOWN_EXECUTION_SCOPE")
    if weekday_session and not recent:
        market_status = "STALE_OR_MISSING_REPORT"
    return {
        "schema": "SKY_READ_ONLY_RECOVERY_WATCHDOG_V1",
        "checked_at_tpe": now.isoformat(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_event_name": os.getenv("GITHUB_EVENT_NAME"),
        "code_contract": "PASS" if not errors else "FAIL",
        "code_errors": errors,
        "monitor_mode": "CONTINUOUS_EVIDENCE_ONLY_NO_AUTOMATIC_CODE_CHANGES",
        "market_session_window": weekday_session,
        "official_calendar_not_verified_here": True,
        "market_status": market_status,
        "market_report_run_id": market.get("run_id"),
        "market_report_generated_at_utc": published,
        "market_report_age_seconds": report_age,
        "universe_count": universe,
        "observed_price_count": observed,
        "bulk_fresh_executed_count": fresh,
        "unified_run_id": unified.get("run_id"),
        "unified_decision": unified.get("decision"),
        "mobile_api_e2e": "NOT_VERIFIED",
        "six_model_inference": "NOT_VERIFIED",
        "production_trade_eligible": False,
        "action": "禁止交易",
        "information_report_scope": "TWSE_TPEX_OBSERVATIONS_NOT_LIVE_TRADES",
        "notes": [
            "Raw bulk prices with no last execution timestamp are informational only.",
            "Scheduled watchdog does not autonomously modify source or deploy Cloud Run.",
            "Existing scan.yml remains the owner of market-hour every-5-minute scans.",
            "An Actions success means this watchdog ran, not that market trading is ready.",
        ],
    }

def write_report(report):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = (
        "# Sky Recovery Watchdog\n\n"
        f"Checked (TPE): {report['checked_at_tpe']}\n\n"
        f"- Code contract: {report['code_contract']}\n"
        f"- Market evidence: {report['market_status']}\n"
        f"- Observed / universe: {report['observed_price_count']} / {report['universe_count']}\n"
        f"- Verified fresh bulk trades: {report['bulk_fresh_executed_count']}\n"
        f"- Mobile E2E: {report['mobile_api_e2e']}\n"
        f"- Production eligibility: NO\n"
        f"- Action: 禁止交易\n"
    )
    (OUTPUT / "latest.md").write_text(summary, encoding="utf-8")

def main():
    report = collect()
    write_report(report)
    print(json.dumps(report, ensure_ascii=False))
    if report["code_contract"] != "PASS":
        raise SystemExit("SKY_WATCHDOG_CODE_CONTRACT_FAILED")

if __name__ == "__main__":
    main()
