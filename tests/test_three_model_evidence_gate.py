import hashlib
from pathlib import Path
from research.three_model_evidence_gate import MODELS, REQUIRED_GATES, audit

def test_missing_manifest_fails_closed(tmp_path):
    report = audit({}, tmp_path)
    assert not report["all_evidence_complete"]
    assert not report["production_signal"]
    assert set(report["models"]) == set(MODELS)
    assert all(not x["evidence_complete"] for x in report["models"].values())

def test_proof_files_and_gates_required(tmp_path):
    p = tmp_path / "model.joblib"
    p.write_bytes(b"fake test payload - never deploy")
    report = tmp_path / "validation.json"
    report.write_text('{"test":true}')
    row = dict(model_id=MODELS[0], training_start="2026-01-01",
        training_end="2026-10-31", data_source="fixture",
        source_fingerprint="sha256:fixture", feature_schema_version="v1",
        train_samples=100, validation_samples=50, oos_samples=30,
        training_code_commit="fixture",
        artifact_path="model.joblib",
        artifact_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        validation_report_path="validation.json",
        validation_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
        gates={g: "PASS" for g in REQUIRED_GATES})
    result = audit({"models": {MODELS[0]: row}}, tmp_path)
    assert result["models"][MODELS[0]]["evidence_complete"]
    assert not result["all_evidence_complete"]
    assert not result["production_signal"]
    row["artifact_sha256"] = "wrong"
    assert "artifact_sha256_mismatch" in audit({"models": {MODELS[0]: row}}, tmp_path)["models"][MODELS[0]]["missing_or_failed"]

def test_path_traversal_rejected(tmp_path):
    row = {"model_id": MODELS[0], "artifact_path": "../private.key"}
    result = audit({"models": {MODELS[0]: row}}, tmp_path)
    assert "artifact_path_outside_root" in result["models"][MODELS[0]]["missing_or_failed"]
