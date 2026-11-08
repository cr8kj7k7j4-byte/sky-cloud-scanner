"""W2 monitoring tests: deterministic fixtures, no GitHub network, cloud, or writes."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from research.w2_rapid_recovery_monitor import (
    PR_NUMBER, REQUIRED_WORKFLOWS, assess, update_issue_body,
)

TPE = ZoneInfo("Asia/Taipei")
HEAD = "a" * 40
NOW = datetime(2026, 11, 8, 11, 0, tzinfo=TPE)


def pr(**overrides):
    value = {"number": PR_NUMBER, "state": "open", "merged": False,
             "head": {"sha": HEAD}, "updated_at": "2026-11-08T02:38:00Z"}
    value.update(overrides)
    return value


def workflow(name, conclusion="success", event="pull_request", sha=HEAD,
             created_at="2026-11-08T02:40:00Z", status="completed"):
    return {
        "id": 42439999999, "name": name, "event": event, "head_sha": sha,
        "status": status, "conclusion": conclusion, "created_at": created_at,
        "html_url": "https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42439999999",
    }


def all_success():
    return [workflow(name) for name in REQUIRED_WORKFLOWS]


def test_all_required_head_checks_success_is_not_production_or_live_e2e():
    result = assess(pr(), all_success(), NOW)
    assert result["status"] == "OFFLINE_CI_PASS_REAL_E2E_HOLD"
    assert all(v == "SUCCESS" for v in result["checks"].values())
    assert result["production_approved"] is False
    assert result["real_gcs_new_audit_verified"] is False
    assert result["first_nov9_schedule_verified"] is False


def test_latest_failed_workflow_is_action_required_with_specific_run_url():
    runs = all_success()
    runs[0] = workflow(REQUIRED_WORKFLOWS[0], conclusion="failure")
    result = assess(pr(), runs, NOW)
    assert result["status"] == "ACTION_REQUIRED_FAILED_CI"
    assert len(result["failed_run_urls"]) == 1


def test_old_branch_failure_cannot_override_current_head_success():
    runs = all_success() + [
        workflow(REQUIRED_WORKFLOWS[0], conclusion="failure",
                 sha="b" * 40, created_at="2026-11-08T02:45:00Z"),
        workflow(REQUIRED_WORKFLOWS[1], conclusion="failure",
                 event="workflow_dispatch", created_at="2026-11-08T02:47:00Z"),
    ]
    assert assess(pr(), runs, NOW)["status"] == "OFFLINE_CI_PASS_REAL_E2E_HOLD"


def test_pending_during_ci_grace_and_missing_after_grace():
    recent = pr(updated_at="2026-11-08T02:54:00Z")
    assert assess(recent, [], NOW)["status"] == "CI_PENDING"
    old = pr(updated_at="2026-11-08T00:00:00Z")
    assert assess(old, [], NOW)["status"] == "ACTION_REQUIRED_MISSING_CI"


def test_current_head_newer_failure_overrides_older_success():
    runs = all_success() + [
        workflow(REQUIRED_WORKFLOWS[0], conclusion="failure",
                 created_at="2026-11-08T02:50:00Z")
    ]
    assert assess(pr(), runs, NOW)["status"] == "ACTION_REQUIRED_FAILED_CI"


def test_monitor_window_closes_without_production_changes():
    result = assess(pr(), all_success(), datetime(2026, 11, 9, 10, 39, tzinfo=TPE))
    assert result["status"] == "MONITOR_WINDOW_CLOSED"
    assert result["production_approved"] is False


def test_closed_pr_requires_w0_review_and_never_self_merges():
    result = assess(pr(state="closed", merged=True), all_success(), NOW)
    assert result["status"] == "PR_CLOSED_REQUIRES_W0_REVIEW"
    assert result["production_approved"] is False


def test_issue_write_is_idempotent_and_preserves_manual_notes():
    result = assess(pr(), all_success(), NOW)
    body, changed = update_issue_body("# W2 dedicated issue\n\nHuman note.\n", result)
    assert changed and "Human note." in body
    body2, changed2 = update_issue_body(body, result)
    assert not changed2 and body == body2
    failed = assess(pr(), [workflow(REQUIRED_WORKFLOWS[0], conclusion="failure")], NOW)
    updated, modified = update_issue_body(body2, failed)
    assert modified and "ACTION_REQUIRED" in updated
    assert updated.count("<!-- W2_MONITOR_REPORT_BEGIN -->") == 1
    assert "Human note." in updated


@pytest.mark.parametrize("bad", [
    {},
    {"number": 999, "state": "open", "head": {"sha": HEAD}},
])
def test_unexpected_pr_identity_fails_closed(bad):
    with pytest.raises(ValueError, match="unexpected_pr_identity"):
        assess(bad, [], NOW)
