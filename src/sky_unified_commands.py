"""Manual governed Sky composite commands; never sends orders or promotes research."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .realtime_quote_evidence import market_scope

BASE = Path("output/unified")
REGISTRIES = (
    "SKY_SYSTEM_REGISTRY_V2_1.md",
    "research/RESEARCH_FREEZE_REGISTRY.md",
    "docs/SKY_VALIDATION_PROTOCOL_V1_0.md",
)


def execute(argv: list[str]) -> dict:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=600, check=False)
        return {"command": argv, "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-20000:], "stderr_tail": proc.stderr[-3000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": argv, "exit_code": 125, "error": str(exc)}


def operational_market_evidence_ok(item: dict) -> bool:
    """A successful process or uploaded artifact is not market coverage."""
    try:
        coverage = float(item.get("quote_coverage_pct"))
    except (TypeError, ValueError):
        return False
    return (
        item.get("available") is True
        and item.get("operational_full_market_scan") is True
        and item.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
        and item.get("live_whole_market_certified") is True
        and 80.0 <= coverage <= 100.0
    )


def market_session_open(now: datetime | None = None) -> bool:
    """Conservative TWSE/TPEx regular-session guard; calendar also required."""
    current = (now or datetime.now(ZoneInfo("Asia/Taipei"))).astimezone(
        ZoneInfo("Asia/Taipei"))
    minutes = current.hour * 60 + current.minute
    return current.weekday() < 5 and 9 * 60 <= minutes < 13 * 60 + 30


def market_mode() -> dict:
    if not market_session_open():
        return {
            "decision": "NO_TRADE_OUTSIDE_TW_REGULAR_SESSION",
            "market_session": "TWSE_TPEx_REGULAR_09_00_13_30",
            "notes": "No live quote scan outside regular trading hours. Research replay is separate.",
            "strategies": {},
            "reports": {},
            "short_strategy": "NOT_EXECUTED_NO_VERIFIED_STANDALONE_RUNNER",
        }
    calendar = execute([sys.executable, "-m", "src.trading_calendar",
                        "--out", str(BASE / "calendar.json")])
    results = {"calendar": calendar, "strategies": {},
               "short_strategy": "NOT_EXECUTED_NO_VERIFIED_STANDALONE_RUNNER",
               "swing_status": "RESEARCH_ONLY", "swing5d_status": "HOLD_RESEARCH_ONLY"}
    path = BASE / "calendar.json"
    if calendar["exit_code"] != 0 or not path.is_file():
        results["decision"] = "NO_TRADE_CALENDAR_UNAVAILABLE"
        return results
    try:
        check = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        results["decision"] = "NO_TRADE_INVALID_CALENDAR"
        return results
    if check.get("source_status") != "PASS" or check.get("should_scan") is not True:
        results["decision"] = "NO_TRADE_NOT_CONFIRMED_TRADING_DAY"
        return results
    for key, command in (
        ("intraday", [sys.executable, "-m", "src.main"]),
        ("swing_research", [sys.executable, "-m", "src.swing_live_scanner", "--mode", "swing"]),
        ("swing5d_research", [sys.executable, "-m", "src.swing_live_scanner", "--mode", "swing5d"]),
    ):
        results["strategies"][key] = execute(command)
    # Preserve a single inspectable evidence index instead of silently merging
    # research candidates into Production signals.
    results["reports"] = {}
    for label, filename in (
        ("intraday", "output/latest.json"),
        ("swing_research", "output/swing_live/latest_swing.json"),
        ("swing5d_research", "output/swing_live/latest_swing5d.json"),
    ):
        item = {"file": filename, "available": False}
        try:
            report = json.loads(Path(filename).read_text(encoding="utf-8"))
            item.update({
                "available": True,
                "data_timestamp": (report.get("generated_at") or report.get("run_time") or report.get("scan_time")),
                "quote_scope": report.get("quote_scope"),
                "source_scope": market_scope(report),
                "live_whole_market_certified": report.get("live_whole_market_certified") is True,
                "operational_full_market_scan": report.get("operational_full_market_scan"),
                "quote_coverage_pct": report.get("quote_coverage_pct"),
                "candidate_count": report.get("candidate_count"),
                "candidate_preview": [
                    {"symbol": row.get("symbol"),
                     "name": row.get("name"),
                     "price": (row.get("fugle_close") if row.get("data_status") == "VERIFIED_EXECUTED_TRADE" else None),
                     "action": row.get("candidate_action", "觀察")}
                    for row in report.get("deep_candidates", [])[:8]
                ],
                "research_only": label != "intraday",
            })
        except (OSError, ValueError, TypeError):
            item["reason"] = "RESULT_NOT_AVAILABLE_OR_INVALID"
        results["reports"][label] = item
    # Process exit zero is not verified whole-market data.
    # Operational coverage alone still never certifies an A+ trade signal.
    results["operational_coverage_verified"] = operational_market_evidence_ok(
        results["reports"]["intraday"]
    )
    results["decision"] = (
        "SCAN_FAILURE_NO_TRADE"
        if any(x["exit_code"] != 0 for x in results["strategies"].values())
        else "DATA_COVERAGE_INSUFFICIENT_NO_TRADE"
        if not results["operational_coverage_verified"]
        else "OPERATIONAL_COVERAGE_ONLY_NO_A_PLUS"
    )
    return results


def source_health_verdict(source_report: dict, schedule_report: dict | None) -> dict:
    """Separate API/process success from fresh trades and official quote coverage."""
    checks = {}
    for key in ("fugle_tickers_TSE", "fugle_tickers_OTC",
                "fugle_quote_2330", "fugle_quote_8089_otc",
                "fugle_snapshot_TSE", "fugle_snapshot_OTC"):
        probe = source_report.get(key) or {}
        checks[key] = {
            "status": probe.get("status", "UNKNOWN"),
            "ok": probe.get("ok") is True,
            "fresh_executed_trade": probe.get("fresh_executed_trade"),
            "api_accessible": probe.get("api_accessible"),
        }
    sample = source_report.get("mis_sample") or {}
    official = source_report.get("official_universe") or {}
    return {
        "diagnostic_time": source_report.get("time"),
        "official_universe": official,
        "universe_count": source_report.get("universe_count"),
        "mis_sample": {"requested": sample.get("requested"),
                       "returned": sample.get("returned")},
        "fugle": checks,
        "schedule": {
            "audited_at_utc": (schedule_report or {}).get("generated_at_utc"),
            "workflow_count": len((schedule_report or {}).get("workflows", [])),
            "attention": [
                {"path": row.get("path"), "verdict": row.get("verdict")}
                for row in (schedule_report or {}).get("workflows", [])
                if row.get("verdict") not in ("RUN_SUCCEEDED",)
            ][:50],
        },
        "all_checks_passed": False,
        "note": "API access and workflow success do not certify live whole-market quote coverage.",
    }


def health_mode() -> dict:
    source = execute([sys.executable, "-m", "src.diagnose_sources"])
    schedule = execute([sys.executable, "research/schedule_health.py"])
    source_data = {}
    schedule_data = None
    try:
        source_data = json.loads(source.get("stdout_tail", ""))
    except (ValueError, TypeError):
        pass
    try:
        schedule_data = json.loads(
            Path("output/schedule_health/latest.json").read_text(encoding="utf-8"))
    except (ValueError, OSError):
        pass
    evidence = source_health_verdict(source_data, schedule_data)
    sources_available = bool(source_data.get("official_universe"))
    if source["exit_code"] != 0 or schedule["exit_code"] != 0:
        decision = "HEALTH_CHECK_FAILED"
    elif not sources_available or schedule_data is None:
        decision = "HEALTH_EVIDENCE_INCOMPLETE"
    else:
        decision = "HEALTH_OBSERVED_NOT_FULLY_CERTIFIED"
    return {"sources": source, "schedule": schedule,
            "evidence": evidence, "decision": decision}


def validation_mode() -> dict:
    missing = [path for path in REGISTRIES if not Path(path).is_file()]
    tests = execute([sys.executable, "-m", "pytest", "-q",
                     "tests/test_sky_command_router.py",
                     "tests/test_sky_unified_commands.py"])
    snapshot_path = Path("docs/SKY_EXTERNAL_LATEST_STATUS.json")
    snapshot = {}
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    dashboard = snapshot.get("w4_dashboard") or {}
    sufficiency = dashboard.get("sample_sufficiency") or {}
    observed = sufficiency.get("observed") or {}
    integrity = dashboard.get("strategy_evidence_integrity") or {}
    provenance = dashboard.get("forward_trade_provenance") or {}
    promotion = dashboard.get("promotion_scorecard") or {}
    evidence = {
        "snapshot_generated_at_utc": snapshot.get("generated_at_utc"),
        "snapshot_source_run_id": (snapshot.get("source") or {}).get(
            "dashboard_workflow_run_id"),
        "sample_sufficient": sufficiency.get("sufficient"),
        "sample_count": observed.get("samples"),
        "trading_days": observed.get("trading_days"),
        "regime_count": observed.get("regime_count"),
        "eligible_strategy_records": integrity.get("eligible_strategy_records"),
        "strategy_evidence_status": integrity.get("status"),
        "authoritative_trade_provenance": provenance.get("status"),
        "after_cost_expectancy_r": (promotion.get("metrics_used") or {}).get(
            "expectancy_r") if integrity.get("eligible_strategy_records", 0) else None,
        "promotable_to_governance_review": promotion.get(
            "promotable_to_governance_review"),
        "production_eligible": False,
        "note": "Only existing forward evidence is summarized; no new backtest or performance certification.",
    }
    if missing or tests["exit_code"] != 0:
        decision = "VALIDATION_CHECK_FAILED"
    elif not snapshot or not dashboard:
        decision = "VALIDATION_EVIDENCE_MISSING"
    else:
        decision = "VALIDATION_INSUFFICIENT_DATA_NO_PROMOTION"
    return {"missing_registry_files": missing, "route_tests": tests,
            "production_baselines": ["Sky Day Trading v1.4", "Sky Swing V1.0"],
            "research_promotion": "NOT_AUTHORIZED",
            "evidence": evidence, "decision": decision}


def run(mode: str) -> dict:
    BASE.mkdir(parents=True, exist_ok=True)
    payload = {"command": mode, "utc_generated_at": datetime.now(timezone.utc).isoformat(),
               "github_run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
               "execution_scope": "MANUAL_READ_ONLY_NO_ORDER_NO_PROMOTION"}
    payload["result"] = {"all_market": market_mode, "system_health": health_mode,
                         "model_validation": validation_mode}[mode]()
    (BASE / f"{mode}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    result = payload["result"]
    summary = f"# Sky {mode}\n\n狀態：{result['decision']}\n\n"
    summary += "此報告為執行與治理證據，不代表有合格買進訊號或通過正期望驗證。\n"
    if mode == "all_market":
        summary += "\n空方研究未有經確認的獨立執行入口，因此未執行且不得輸出空方交易訊號。\n"
    if mode == "system_health":
        evidence = result.get("evidence") or {}
        summary += "\n## 來源權限與行情證據\n"
        for name, check in (evidence.get("fugle") or {}).items():
            summary += f"- {name}：{check.get('status', 'UNKNOWN')}\n"
        sched = evidence.get("schedule") or {}
        summary += f"\nGitHub 排程檢查數：{sched.get('workflow_count', '待確認')}\n"
        summary += f"排程異常或待確認數：{len(sched.get('attention') or [])}\n"
        summary += "\n流程完成不代表上市＋上櫃全市場即時成交價完整。\n"
    if mode == "model_validation":
        evidence = result.get("evidence") or {}
        summary += "\n## W4 前瞻證據（並非真實獲利）\n"
        for name, key in (
            ("證據來源時間 UTC", "snapshot_generated_at_utc"),
            ("觀察樣本", "sample_count"),
            ("真正交易日", "trading_days"),
            ("市場環境數", "regime_count"),
            ("可辨識策略交易筆數", "eligible_strategy_records"),
            ("交易決策溯源", "authoritative_trade_provenance"),
            ("是否符合升版條件", "production_eligible"),
        ):
            summary += f"- {name}：{evidence.get(key, '待確認')}\n"
        summary += "\n未重跑完整成本後回測；策略正期望仍待正式驗證。\n"
    (BASE / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    for key, value in result.items():
        if isinstance(value, dict) and value.get("exit_code", 0) != 0:
            print(f"[FAILED CHECK] {key}: exit={value['exit_code']}")
            print(value.get("stderr_tail", "")[-1600:])
            print(value.get("stdout_tail", "")[-1600:])
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as f:
        f.write(summary)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True,
                        choices=["all_market", "system_health", "model_validation"])
    mode = parser.parse_args().mode
    payload = run(mode)
    if payload["result"]["decision"] in (
        "SCAN_FAILURE_NO_TRADE", "DATA_COVERAGE_INSUFFICIENT_NO_TRADE",
        "HEALTH_CHECK_FAILED", "HEALTH_EVIDENCE_INCOMPLETE",
        "VALIDATION_CHECK_FAILED", "VALIDATION_EVIDENCE_MISSING",
        "NO_TRADE_CALENDAR_UNAVAILABLE", "NO_TRADE_INVALID_CALENDAR",
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
