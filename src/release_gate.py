from __future__ import annotations


def release_gate(
    readiness,
    *,
    ci_passed=False,
    paper_sample_sufficient=False,
    rollback_drill_passed=False,
    incident_runbook_present=False,
    manual_approval=False,
):
    r = dict(readiness or {})
    checks = {
        "readiness_100": float(r.get("score") or 0.0) == 100.0,
        "no_failed_domains": not r.get("failed_domains"),
        "no_critical_failures": not r.get("critical_failed"),
        "ci_passed": bool(ci_passed),
        "paper_sample_sufficient": bool(paper_sample_sufficient),
        "rollback_drill_passed": bool(rollback_drill_passed),
        "incident_runbook_present": bool(incident_runbook_present),
        "manual_approval": bool(manual_approval),
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "release_review_passed": not failed,
        "production_release_allowed": False,
        "checks": checks,
        "failed_checks": failed,
        "note": (
            "Passing Release Gate permits controlled release review only. "
            "Live production activation remains an explicit manual action."
        ),
    }
