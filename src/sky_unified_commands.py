"""Manual governed Sky composite commands; never sends orders or promotes research."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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
    results["decision"] = ("PARTIAL_UNVERIFIED_NO_A_PLUS" if
                           all(x["exit_code"] == 0 for x in results["strategies"].values())
                           else "SCAN_FAILURE_NO_TRADE")
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
        "SCAN_FAILURE_NO_TRADE", "HEALTH_CHECK_FAILED", "VALIDATION_CHECK_FAILED",
        "NO_TRADE_CALENDAR_UNAVAILABLE", "NO_TRADE_INVALID_CALENDAR",
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
