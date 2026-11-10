"""W0 read-only integration audit: provider observation, PAPER_ONLY risk, scheduled overlap.

This does not call paid market APIs, does not issue orders, does not modify
Production, and does not require a brokerage account. Scheduled event evidence
is separate from strategy certification and actual API call deduplication.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import math
import os
import re
import subprocess

from research.sky_paper_only_acceptance import paper_gate
from research.sky_paper_trade_trace import evaluate_paper_journal


REPO = Path(__file__).resolve().parents[1]
TARGETS = ("scan.yml", "sky-full-market-five-minute-dispatch.yml",
           "sky-full-market-private.yml")
AUDIT_SCHEMA = "SKY_W0_SHARED_BLOCKER_CONVERGENCE_V1"


def cron_patterns(text):
    """Read YAML scheduled cron entries without interpreting strings in other jobs."""
    lines = text.splitlines()
    at = next((i for i, line in enumerate(lines)
               if line.startswith("  schedule:")), None)
    if at is None:
        return []
    values = []
    for line in lines[at + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= 2:
            break
        if "cron:" in line:
            value = line.split("cron:", 1)[1].strip()
            if value and value[0] in ("'", '"'):
                value = value[1:-1]
            if value:
                values.append(value)
    return values


def _safe_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    return None


def _dt(raw):
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return value if value.tzinfo and value.utcoffset() is not None else None
    except (ValueError, TypeError):
        return None


def classify_market(status):
    """Snapshot observations never certify whole-market executed trade times."""
    if not isinstance(status, dict):
        status = {}
    count = _safe_int(status.get("universe_count"))
    sampled = _safe_int(status.get("stage2_verified_executed_count"))
    if count is None or sampled is None or sampled > count:
        return {"classification": "INPUT_INCOMPLETE", "verified_quote_count": sampled,
                "whole_market_execution_certified": False,
                "research_observation_available": False}
    return {
        "classification": ("BOUNDED_QUOTE_SAMPLE_ONLY" if sampled > 0
                           else "NO_VERIFIED_EXECUTION_SAMPLE"),
        "universe": count,
        "verified_quote_count": sampled,
        "whole_market_execution_certified": False,
        "research_observation_available": count > 0,
        "note": "Sampled quote confirmations do not establish whole-market trade-time coverage.",
    }


def _run_summary(runs, name):
    arr = [r for r in runs if r.get("name") == name and r.get("event") == "schedule"]
    # Only summarize observed events; do not extrapolate unobserved slots.
    return {
        "sampled_schedule_events": len(arr),
        "sampled_success": sum(r.get("status") == "completed" and r.get("conclusion") == "success" for r in arr),
        "sampled_failed": sum(r.get("status") == "completed" and r.get("conclusion") == "failure" for r in arr),
        "sampled_unknown": sum(r.get("status") != "completed" for r in arr),
        "latest_run_id": arr[0].get("id") if arr else None,
        "latest_created_at": arr[0].get("created_at") if arr else None,
    }


def audit(status, paper_ledger=None, paper_cost=None, paper_events=None,
          workflow_source=None, scheduled_runs=None):
    """Return an evidence-centric HOLD report; never claim uptime or real fills."""
    if not isinstance(status, dict):
        status = {}
    workflow_source = workflow_source or {}
    scheduled_runs = scheduled_runs if isinstance(scheduled_runs, list) else []
    crons = {path: cron_patterns(workflow_source.get(path, ""))
             for path in TARGETS}
    overlapping = bool(crons["scan.yml"] and
                       crons["scan.yml"] == crons["sky-full-market-five-minute-dispatch.yml"])
    market = classify_market(status)
    paper = paper_gate(paper_ledger, paper_cost)
    journal = evaluate_paper_journal(paper_events)
    # A journal can reconcile hypothetical numbers; without independent source
    # validation it is NOT certified forward Paper performance.
    return {
        "schema": AUDIT_SCHEMA,
        "source_market_run": status.get("run_url"),
        "source_market_data_timestamp": status.get("data_timestamp"),
        "source_market_timestamp_valid": _dt(status.get("data_timestamp")) is not None,
        "broker_account_required_for_research": False,
        "market": market,
        "paper_admission": paper,
        "paper_journal_status": journal["paper_journal_status"],
        "paper_cost_arithmetic_reconciled": journal["paper_cost_arithmetic_reconciled"],
        "paper_performance_verified": journal["after_cost_paper_performance_verified"],
        "paper_event_count": journal["trade_count"],
        "schedule": {
            "declared_crons": crons,
            "same_cron_duplicate_dispatch_risk": overlapping,
            "formal_scan": _run_summary(scheduled_runs, "Sky Cloud Scanner v0.5 + P0-R"),
            "paid_research_dispatch": _run_summary(scheduled_runs, "Sky Paid Full Market Research Dispatcher Every 5 Minutes"),
            "actual_duplicate_paid_requests_confirmed": False,
            "api_usage_bill_verified": False,
            "all_55_slots_certified": False,
            "downstream_private_gcs_readback_certified": False,
            "verdict": "EVIDENCE_INCOMPLETE_NEEDS_EVENT_AND_BILLING_RECONCILIATION",
        },
        "blockers": {
            "full_market_executed_quote_time": not market["whole_market_execution_certified"],
            "p0r_paper_admission": not paper["paper_eligible"],
            "model_5m_vwap_full_rule": status.get("candidate_chain_vwap_certified") in (None, 0),
            "paper_source_verified_expectancy": not journal["after_cost_paper_performance_verified"],
            "actual_five_minute_schedule": True,
        },
        "research_access": "OBSERVATION_ALLOWED_NO_BROKER",
        "formal_market_gate": "HOLD_NO_FULL_MARKET_EXECUTION_CERTIFICATION",
        "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
        "note": "Formal scanner failure is a valid fail-closed gate result, not evidence provider API failed. The same cron is a possible overlapping expense, not proof two billable API calls happened. Paper input is optional for research observation, mandatory for Paper entry/performance certification.",
    }


def _gh_schedules():
    """Read-only GitHub Actions metadata. Missing token is NOT a green audit."""
    if not os.getenv("GH_TOKEN") or not os.getenv("GITHUB_REPOSITORY"):
        return [], "NOT_QUERIED_MISSING_GITHUB_CONTEXT"
    command = ["gh", "api", f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs?event=schedule&per_page=100"]
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=35)
        if proc.returncode:
            return [], "GITHUB_QUERY_FAILED_" + str(proc.returncode)
        parsed = json.loads(proc.stdout)
        if not isinstance(parsed.get("workflow_runs"), list):
            return [], "INVALID_RUN_PAYLOAD"
        return parsed["workflow_runs"], "LATEST_100_SCHEDULE_EVENTS_ONLY"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [], "GITHUB_QUERY_ERROR"


def main():
    path = REPO / "docs" / "SKY_CHAT_LATEST_STATUS.json"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        status = {}
    flows = {}
    for filename in TARGETS:
        f = REPO / ".github" / "workflows" / filename
        flows[filename] = f.read_text(encoding="utf-8") if f.is_file() else ""
    runs, evidence_scope = _gh_schedules()
    report = audit(status, workflow_source=flows, scheduled_runs=runs)
    report["schedule"]["github_events_query_status"] = evidence_scope
    out = REPO / "output" / "w0_shared_blocker_audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# W0｜三個共通阻礙研究級整合稽核", "",
             "- 行情掃描：" + str(report["source_market_run"] or "待確認"),
             "- 富果行情時間：" + str(report["source_market_data_timestamp"] or "待確認"),
             "- 全市場有效成交時間：" + report["formal_market_gate"],
             "- PAPER_ONLY 模擬新進場：" + str(report["paper_admission"]["paper_eligible"]),
             "- 模擬績效：" + report["paper_journal_status"],
             "- 相同排程表：" + str(report["schedule"]["same_cron_duplicate_dispatch_risk"]),
             "- 重複付費 API 是否已確認：" + str(report["schedule"]["actual_duplicate_paid_requests_confirmed"]),
             "- GitHub 事件樣本：" + evidence_scope,
             "- 正式交易：" + report["trade_action"], "",
             "此報告沒有真實券商帳戶需求；PAPER_ONLY 的輸入與來源證據仍需補齊。",
             "沒有完成資料時間、完整 K 棒、成本後 RR、55 時段和 W0/P0-G 前，不得自動升 Production。"]
    (out / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
