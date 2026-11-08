"""Offline contract tests: no paid workflows, cloud identities or order routing."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ops.w0_research_quickwatch import DEADLINE, TARGET_WORKFLOWS, evaluate

NOW = datetime(2026, 11, 8, 10, 45, tzinfo=ZoneInfo("Asia/Taipei"))


def run(**overrides):
    return {
        "head_branch": "main",
        "event": "workflow_dispatch",
        "created_at": "2026-11-08T02:40:00Z",
        "status": "completed",
        "conclusion": "failure",
        "id": 123456,
        "html_url": "https://github.com/example/repo/actions/runs/123456",
        **overrides,
    }


def test_new_real_main_failure_is_reported_without_triggering_repairs():
    data = {TARGET_WORKFLOWS[0]: [run()]}
    result = evaluate(NOW, data)
    assert result["status"] == "ANOMALY_DETECTED"
    assert result["anomalies"][0]["run_id"] == 123456
    assert result["trading_enabled"] is False
    assert result["scheduled_17_30_18_30_19_45_verified"] is False


def test_pr_failures_do_not_claim_main_runtime_failure():
    result = evaluate(NOW, {TARGET_WORKFLOWS[0]: [run(event="pull_request")]})
    assert result["status"] == "NO_RECENT_FAILED_MAIN_RUNS"
    assert not result["anomalies"]


def test_old_failure_does_not_repeat_forever():
    result = evaluate(NOW, {TARGET_WORKFLOWS[1]: [
        run(created_at="2026-11-07T00:00:00Z")
    ]})
    assert not result["anomalies"]


def test_pending_jobs_are_not_labelled_success_or_failure():
    result = evaluate(NOW, {TARGET_WORKFLOWS[2]: [
        run(status="in_progress", conclusion=None)
    ]})
    assert result["status"] == "NO_RECENT_FAILED_MAIN_RUNS"
    assert result["runs"][0]["status"] == "in_progress"


def test_monitor_stops_at_deadline_no_more_paid_or_workflow_inquiries():
    result = evaluate(DEADLINE, {TARGET_WORKFLOWS[0]: [run()]})
    assert result["status"] == "MONITOR_WINDOW_EXPIRED"
    assert not result["anomalies"]
    assert not result["runs"]


def test_other_branches_are_not_treated_as_default_branch():
    result = evaluate(NOW, {TARGET_WORKFLOWS[0]: [
        run(head_branch="w2/research-guard")
    ]})
    assert result["status"] == "NO_RECENT_FAILED_MAIN_RUNS"


def test_no_run_is_not_fake_schedule_success():
    result = evaluate(NOW, {})
    assert result["status"] == "NO_RECENT_FAILED_MAIN_RUNS"
    assert result["scheduled_17_30_18_30_19_45_verified"] is False
