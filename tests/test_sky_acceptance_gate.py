import json
from pathlib import Path

from research.sky_acceptance_gate import COMMANDS, inspect, signal_receipt


def _observation(**updates):
    base = {
        "model_id": "TEST_RESEARCH",
        "model_version": "v1",
        "symbol": "1101",
        "observed_at": "2026-11-06T10:00:00+08:00",
        "source": "FUGLE_TEST_FIXTURE",
        "source_timestamp": "2026-11-06T09:59:00+08:00",
        "signal_class": "RESEARCH_ONLY",
        "signal_id": "fixture-id-001",
        "execution_authorized": False,
    }
    return base | updates


def test_signal_audit_deduplicates_idempotent_observations():
    row = _observation()
    result = signal_receipt([row, dict(row)])
    assert result["status"] == "PASS"
    assert result["rows_seen"] == 2
    assert result["unique_signal_ids"] == 1


def test_signal_audit_rejects_same_id_different_payload():
    result = signal_receipt([_observation(), _observation(symbol="2330")])
    assert result["status"] == "FAIL_CLOSED"
    assert "CONFLICTING_SIGNAL_ID" in result["problems"][0]


def test_research_never_asserts_real_execution():
    assert signal_receipt([_observation(execution_authorized=True)])["status"] == "FAIL_CLOSED"
    assert signal_receipt([_observation(fill_status="FILLED")])["status"] == "FAIL_CLOSED"


def test_missing_provenance_rejected():
    result = signal_receipt([_observation(source_timestamp=None)])
    assert result["status"] == "FAIL_CLOSED"


def test_production_label_alone_does_not_prove_authorization():
    assert signal_receipt([_observation(signal_class="PRODUCTION")])["status"] == "FAIL_CLOSED"


def test_invalid_records_container_fails_closed(tmp_path):
    path = tmp_path / "signals.json"
    path.write_text(json.dumps({"records": {"bad": "not a list"}}))
    report = inspect(Path("."), path)
    assert report["signal_audit"]["status"] == "FAIL_CLOSED"


def test_existing_route_contracts_do_not_create_production_rights():
    report = inspect(Path("."))
    assert len(report["routes"]) == len(COMMANDS)
    assert report["technical_route_and_registry_status"] == "PASS_STATIC_AUDIT"
    assert report["checks"]["production_strategy_promotion"] == "NOT_AUTHORIZED"
    assert report["checks"]["full_market_live_execution_quotes"] == "NOT_TESTED_BY_THIS_GATE"
