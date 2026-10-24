from __future__ import annotations


def system_mode(
    *,
    official_data_ok,
    quote_freshness_ok,
    risk_engine_ok,
    execution_costs_ok,
    monitoring_ok,
    state_store_ok,
    secrets_ok=True,
):
    failures = []

    checks = {
        "official_data_ok": bool(official_data_ok),
        "quote_freshness_ok": bool(quote_freshness_ok),
        "risk_engine_ok": bool(risk_engine_ok),
        "execution_costs_ok": bool(execution_costs_ok),
        "monitoring_ok": bool(monitoring_ok),
        "state_store_ok": bool(state_store_ok),
        "secrets_ok": bool(secrets_ok),
    }
    failures = [k for k, v in checks.items() if not v]

    critical = {
        "official_data_ok",
        "risk_engine_ok",
        "execution_costs_ok",
        "secrets_ok",
    }

    if any(x in critical for x in failures):
        mode = "LOCKDOWN"
    elif failures:
        mode = "OBSERVE_ONLY"
    else:
        mode = "NORMAL"

    return {
        "mode": mode,
        "checks": checks,
        "failures": failures,
        "new_entries_allowed": mode == "NORMAL",
        "live_activation_allowed": False,
        "note": (
            "Any degraded state disables new entries. "
            "Live activation is never automatic."
        ),
    }


def recovery_gate(
    *,
    incident_resolved,
    data_freshness_restored,
    risk_engine_verified,
    execution_costs_verified,
    monitoring_verified,
    state_store_verified,
    rollback_or_fix_verified,
    manual_approval=False,
):
    checks = {
        "incident_resolved": bool(incident_resolved),
        "data_freshness_restored": bool(data_freshness_restored),
        "risk_engine_verified": bool(risk_engine_verified),
        "execution_costs_verified": bool(execution_costs_verified),
        "monitoring_verified": bool(monitoring_verified),
        "state_store_verified": bool(state_store_verified),
        "rollback_or_fix_verified": bool(rollback_or_fix_verified),
        "manual_approval": bool(manual_approval),
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "recovery_review_passed": not failed,
        "resume_new_entries_allowed": False,
        "checks": checks,
        "failed_checks": failed,
        "note": (
            "Recovery review never resumes live trading automatically. "
            "Reactivation requires an explicit separate action."
        ),
    }
