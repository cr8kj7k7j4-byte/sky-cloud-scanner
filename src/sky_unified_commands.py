"""Manual governed Sky composite commands; never sends orders or promotes research."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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
                "stdout_tail": proc.stdout[-3000:], "stderr_tail": proc.stderr[-3000:]}
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


def market_mode() -> dict:
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


def health_mode() -> dict:
    source = execute([sys.executable, "-m", "src.diagnose_sources"])
    schedule = execute([sys.executable, "research/schedule_health.py"])
    return {"sources": source, "schedule": schedule,
            "decision": "CHECK_OUTPUTS_NOT_AUTOMATICALLY_HEALTHY" if
            source["exit_code"] == 0 and schedule["exit_code"] == 0
            else "HEALTH_CHECK_FAILED"}


def validation_mode() -> dict:
    missing = [path for path in REGISTRIES if not Path(path).is_file()]
    tests = execute([sys.executable, "-m", "pytest", "-q",
                     "tests/test_sky_command_router.py",
                     "tests/test_sky_unified_commands.py"])
    return {"missing_registry_files": missing, "route_tests": tests,
            "production_baselines": ["Sky Day Trading v1.4", "Sky Swing V1.0"],
            "research_promotion": "NOT_AUTHORIZED",
            "after_cost_expectancy": "NOT_RECALCULATED",
            "decision": "GOVERNANCE_CHECK_ONLY" if not missing and
            tests["exit_code"] == 0 else "VALIDATION_CHECK_FAILED"}


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
        "HEALTH_CHECK_FAILED", "VALIDATION_CHECK_FAILED",
        "NO_TRADE_CALENDAR_UNAVAILABLE", "NO_TRADE_INVALID_CALENDAR",
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
