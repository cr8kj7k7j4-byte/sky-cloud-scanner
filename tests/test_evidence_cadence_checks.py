from research.evidence_cadence_checks import (
    expected_five_minute_slots,
    expected_formal_daytrade_slots,
    validate_source_timestamp,
    evaluate_scan_artifact_readiness,
    evaluate_cadence_observations,
)


def test_slot_boundaries():
    slots = expected_five_minute_slots()
    assert len(slots) == 55
    assert slots[0] == "09:00" and slots[-1] == "13:30"
    assert len(set(slots)) == 55


def test_timestamp_requires_timezone():
    assert validate_source_timestamp("2026-11-23T09:05:00+08:00")
    assert validate_source_timestamp("2026-11-23T01:05:00Z")
    assert not validate_source_timestamp("2026-11-23T09:05:00")
    assert not validate_source_timestamp("broken")


def test_artifact_fail_closed():
    assert evaluate_scan_artifact_readiness(eligible_successful_scans=0, artifact_files=0, records_loaded=0)["status"] == "WAITING_FOR_FIRST_ELIGIBLE_SCAN"
    assert evaluate_scan_artifact_readiness(eligible_successful_scans=1, artifact_files=0, records_loaded=0)["status"] == "SCAN_ARTIFACT_MISSING"
    assert evaluate_scan_artifact_readiness(eligible_successful_scans=1, artifact_files=1, records_loaded=0)["status"] == "SCAN_RECORDS_MISSING"
    unverified = evaluate_scan_artifact_readiness(eligible_successful_scans=1, artifact_files=1, records_loaded=1)
    assert unverified["status"] == "SAME_RUN_ARTIFACT_UNVERIFIED"
    assert not unverified["evidence_ready"]
    result = evaluate_scan_artifact_readiness(eligible_successful_scans=1, artifact_files=1, records_loaded=1, same_run_verified=True)
    assert result["evidence_ready"]
    assert not result["production_eligible"]
    assert not result["live_order_enabled"]


def test_cadence_gaps():
    not_attested = evaluate_cadence_observations(expected_five_minute_slots())
    assert not not_attested["cadence_evidence_complete"]
    complete = evaluate_cadence_observations(expected_five_minute_slots(), scheduler_evidence_verified=True)
    assert complete["cadence_evidence_complete"]
    gaps = evaluate_cadence_observations(["09:00", "09:05"])
    assert len(gaps["missing_slots"]) == 53
    assert not gaps["cadence_evidence_complete"]


def test_cadence_profiles_are_not_interchangeable():
    formal = expected_formal_daytrade_slots()
    assert formal == ["09:05", "09:15", "09:30", "09:50", "10:15"]
    formal_result = evaluate_cadence_observations(
        formal, scheduler_evidence_verified=True, cadence_profile="FORMAL_DAYTRADE_5")
    assert formal_result["cadence_evidence_complete"]
    assert formal_result["expected_slots"] == 5
    legacy_result = evaluate_cadence_observations(
        formal, scheduler_evidence_verified=True, cadence_profile="RESEARCH_55_SLOTS")
    assert not legacy_result["cadence_evidence_complete"]
    assert len(legacy_result["missing_slots"]) == 50
    assert not evaluate_cadence_observations(formal, cadence_profile="FORMAL_DAYTRADE_5")["cadence_evidence_complete"]


def test_unknown_cadence_profile_fails_closed():
    try:
        evaluate_cadence_observations(["09:05"], scheduler_evidence_verified=True, cadence_profile="UNKNOWN")
    except ValueError as exc:
        assert "UNKNOWN_CADENCE_PROFILE" in str(exc)
    else:
        raise AssertionError("unknown cadence must fail closed")
