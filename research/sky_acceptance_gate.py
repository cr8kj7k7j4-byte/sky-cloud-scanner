"""Sky read-only acceptance gate: evidence classes must never be conflated.

This tool DOES NOT call paid APIs, predict prices, alter Production or trade.
It creates a deterministic inventory/check receipt from the checked-out tree.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.sky_command_router import route_command


COMMANDS = {
    "Sky 快掃": "SKY_QUICK_SCAN",
    "Sky 當沖現在掃一次": "SKY_DAYTRADE_SCAN",
    "Sky 當沖更新 2330": "SKY_SINGLE_STOCK_UPDATE",
    "Sky 波段現在掃一次": "SKY_SWING_V11_LIVE_ALIAS",
    "Sky Swing 5D 快掃": "SKY_SWING_5D",
    "Sky 警戒": "SKY_MONITOR",
    "Sky 持倉監控": "SKY_MONITOR",
    "Sky 波段持倉更新 2330，成本50，1張": "SKY_POSITION_UPDATE",
    "Sky 回測目前模型": "SKY_RESEARCH_VALIDATION",
    "Sky 系統健康檢查": "SKY_UNIFIED_SYSTEM_HEALTH",
    "Sky 全模型驗證": "SKY_UNIFIED_MODEL_VALIDATION",
    "Sky 全市場掃描": "SKY_UNIFIED_MARKET_SCAN",
    "Sky 當沖空方研究 掃一下": "SKY_SHORT_RESEARCH",
}
REQUIRED = (
    "SKY_SYSTEM_REGISTRY_V2_1.md",
    "research/RESEARCH_FREEZE_REGISTRY.md",
    "docs/SKY_VALIDATION_PROTOCOL_V1_0.md",
    "docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md",
    "src/risk_engine.py",
    "src/config.py",
)
ALLOWED_SIGNAL_CLASSES = {"RESEARCH_ONLY", "PRODUCTION"}


def signal_receipt(records: list[dict]) -> dict:
    """Audit observations, not fills. Fail closed on missing provenance or conflict."""
    seen = {}
    problems = []
    authorized = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            problems.append(f"row_{index}:NOT_AN_OBJECT")
            continue
        required = ("model_id", "model_version", "symbol", "observed_at",
                    "source", "source_timestamp", "signal_class", "signal_id")
        missing = [key for key in required if not record.get(key)]
        if missing:
            problems.append(f"row_{index}:MISSING_{','.join(missing)}")
            continue
        signal_id = str(record["signal_id"])
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if signal_id in seen:
            if seen[signal_id] != encoded:
                problems.append(f"row_{index}:CONFLICTING_SIGNAL_ID")
            continue
        seen[signal_id] = encoded
        if record.get("signal_class") not in ALLOWED_SIGNAL_CLASSES:
            problems.append(f"row_{index}:INVALID_SIGNAL_CLASS")
        if record.get("signal_class") == "RESEARCH_ONLY" and (
            record.get("execution_authorized") is True
            or record.get("fill_status") in {"FILLED", "EXECUTED"}
        ):
            problems.append(f"row_{index}:RESEARCH_MUST_NOT_ASSERT_EXECUTION")
        if record.get("signal_class") == "PRODUCTION":
            # A label is not authorization; W0/P0-G evidence must exist separately.
            if not record.get("governance_approval_ref"):
                problems.append(f"row_{index}:MISSING_GOVERNANCE_APPROVAL")
            else:
                authorized += 1
    return {
        "status": "PASS" if not problems else "FAIL_CLOSED",
        "rows_seen": len(records), "unique_signal_ids": len(seen),
        "production_labels_with_governance_ref": authorized,
        "problems": problems,
        "note": "No fill, strategy expectancy or broker order has been verified by this audit.",
    }


def inspect(root: Path, signal_file: Path | None = None) -> dict:
    missing_files = [p for p in REQUIRED if not (root / p).is_file()]
    routes = {}
    for command, expected in COMMANDS.items():
        actual = route_command(command)
        routes[command] = {
            "expected": expected,
            "actual": actual.command_family,
            "result": "PASS_ROUTE_ONLY" if actual.command_family == expected else "FAIL_ROUTE",
            "data_mode": actual.data_mode,
            "realtime_required": actual.realtime_required,
        }
    bad_routes = [k for k, v in routes.items() if v["result"] != "PASS_ROUTE_ONLY"]
    risk = {
        "status": "REQUIRES_RUNTIME_AND_GOVERNANCE_VERIFICATION",
        "issues_to_verify": [
            "EXEC_ENFORCE_GATE is default-off in src/config.py; inspect live env and gate call-sites",
            "CAUTION_LOSS_STREAK defaults to 3 while approved stop-new-entry policy is 2 consecutive stops",
            "RiskPolicy defaults must be reconciled with src/config.py at actual call-sites",
            "Missing current portfolio positions and execution cost cannot authorize size or net RR",
        ],
    }
    probe_path = root / "docs/SKY_FUGLE_2026_HISTORY_PROBE_LATEST.json"
    historical = {"status": "UNVERIFIED"}
    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            results = probe.get("results") or []
            historical = {
                "status": "PARTIAL_SOURCE_EVIDENCE_ONLY",
                "source_report_at_utc": probe.get("generated_at_utc"),
                "reported_symbols": [r.get("symbol") for r in results if isinstance(r, dict)],
                "full_market_pit_verified": False,
                "six_model_backtest_complete": False,
            }
        except (OSError, ValueError):
            historical = {"status": "INVALID_SOURCE_REPORT"}
    signal_audit = {"status": "NOT_PROVIDED", "note": "Cannot infer signal receipt without real records."}
    if signal_file is not None:
        try:
            data = json.loads(signal_file.read_text(encoding="utf-8"))
            records = data if isinstance(data, list) else data.get("records")
            signal_audit = signal_receipt(records if isinstance(records, list) else [])
            if not isinstance(records, list):
                signal_audit["status"] = "FAIL_CLOSED"
                signal_audit["problems"].append("INVALID_RECORDS_CONTAINER")
        except (OSError, ValueError, TypeError) as exc:
            signal_audit = {"status": "FAIL_CLOSED", "problems": [type(exc).__name__]}
    technical = "PASS_STATIC_AUDIT" if not missing_files and not bad_routes else "FAIL_STATIC_AUDIT"
    return {
        "schema": "SKY_ACCEPTANCE_GATE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha": os.environ.get("GITHUB_SHA", "LOCAL_UNVERIFIED"),
        "technical_route_and_registry_status": technical,
        "missing_files": missing_files, "routes": routes,
        "historical_data": historical, "risk": risk, "signal_audit": signal_audit,
        "checks": {
            "model_identity_six_independently_deployed": "INSUFFICIENT_DATA",
            "code_routing": technical,
            "fugle_paid_realtime_entitlement": "NOT_TESTED_BY_THIS_GATE",
            "full_market_live_execution_quotes": "NOT_TESTED_BY_THIS_GATE",
            "immutable_forward_signal_ledger": signal_audit["status"],
            "outcome_backfill": "NOT_TESTED_BY_THIS_GATE",
            "net_expectancy_and_no_trade_counterfactual": "INSUFFICIENT_DATA",
            "cloud_run_mobile_13_columns": "NOT_TESTED_BY_THIS_GATE",
            "github_schedule_real_trigger": "NOT_TESTED_BY_THIS_GATE",
            "production_strategy_promotion": "NOT_AUTHORIZED",
        },
        "no_order_or_production_promotion": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="output/acceptance/sky_acceptance.json")
    parser.add_argument("--signals", default=None)
    args = parser.parse_args()
    report = inspect(Path(args.root), Path(args.signals) if args.signals else None)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = [
        "# Sky 系統驗收總閘門",
        f"程式／路由靜態驗收：{report['technical_route_and_registry_status']}",
        f"已檢查指令：{len(report['routes'])}",
        "本報告不包含實際雲端行情、交易撮合、六模型完整回測或手機 E2E 驗收。",
        "研究訊號不得自動升級正式交易；待確認狀態不能當作通過。",
    ]
    Path(out.with_suffix(".md")).write_text("\n\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    if report["technical_route_and_registry_status"] != "PASS_STATIC_AUDIT":
        raise SystemExit(1)
    if report["signal_audit"]["status"] == "FAIL_CLOSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
