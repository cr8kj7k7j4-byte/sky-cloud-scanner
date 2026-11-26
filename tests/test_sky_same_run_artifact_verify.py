"""Offline-only integrity tests: no Fugle, network, or GitHub call."""
import hashlib
import json
from pathlib import Path

import pytest

from src.sky_same_run_artifact_verify import verify_downloaded_inventory

SHA = "a" * 40


def fixture(tmp_path: Path):
    source = tmp_path / "output/latest.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b'{"ok":true}')
    inv = {
        "schema": "SKY_W0_SAME_RUN_SOURCE_INVENTORY_V1",
        "run_id": "123", "run_attempt": "2", "head_sha": SHA,
        "production_eligible": False, "trade_action": "禁止交易",
        "source_inventory": {
            "snapshot": {
                "path": "output/latest.json",
                "status": "FILE_PRESENT_NOT_SOURCE_CERTIFIED",
                "raw_provider_source_certified": False,
                "byte_count": len(source.read_bytes()),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            },
            "uncaptured": {
                "path": "output/absent.json",
                "status": "HOLD_SOURCE_NOT_CAPTURED",
                "raw_provider_source_certified": False,
            },
        },
    }
    path = tmp_path / "output/sky_quickscan_information/same_run_source_inventory.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(inv), encoding="utf-8")
    return source, path, inv


def check(root):
    return verify_downloaded_inventory(root, expected_run_id="123",
                                       expected_attempt="2", expected_head_sha=SHA,
                                       artifact_id=456)


def test_same_run_integrity_passes_without_source_certification(tmp_path):
    fixture(tmp_path)
    result = check(tmp_path)
    assert result["verified_file_count"] == 1
    assert result["missing_sources"] == ["uncaptured"]
    assert result["provider_data_certified"] is False
    assert result["trade_action"] == "禁止交易"


@pytest.mark.parametrize("field,value", [
    ("run_id", "999"), ("run_attempt", "1"), ("head_sha", "b" * 40),
    ("production_eligible", True), ("trade_action", "買進"),
])
def test_forged_provenance_or_trade_claim_rejected(tmp_path, field, value):
    _, path, inv = fixture(tmp_path)
    inv[field] = value
    path.write_text(json.dumps(inv), encoding="utf-8")
    with pytest.raises(ValueError):
        check(tmp_path)


def test_tampered_bytes_and_missing_file_rejected(tmp_path):
    source, _, _ = fixture(tmp_path)
    source.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SOURCE_DIGEST_MISMATCH"):
        check(tmp_path)
    source.unlink()
    with pytest.raises(ValueError, match="SOURCE_FILE_MISSING"):
        check(tmp_path)


@pytest.mark.parametrize("bad_path", ["../elsewhere", "/etc/passwd", "output/../outside", "C:\\host"])
def test_unsafe_source_paths_rejected(tmp_path, bad_path):
    _, path, inv = fixture(tmp_path)
    inv["source_inventory"]["snapshot"]["path"] = bad_path
    path.write_text(json.dumps(inv), encoding="utf-8")
    with pytest.raises(ValueError, match="UNSAFE_SOURCE_PATH"):
        check(tmp_path)


def test_invalid_artifact_identity_rejected(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError, match="INVALID_EXPECTED_PROVENANCE"):
        verify_downloaded_inventory(tmp_path, expected_run_id="123",
                                    expected_attempt="2", expected_head_sha=SHA,
                                    artifact_id=0)


def test_existing_uncaptured_source_cannot_be_claimed_missing(tmp_path):
    _, _, _ = fixture(tmp_path)
    (tmp_path / "output/absent.json").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_MISSING_STATUS_MISMATCH"):
        check(tmp_path)


def test_all_sources_missing_rejected_instead_of_success(tmp_path):
    source, path, inv = fixture(tmp_path)
    source.unlink()
    inv["source_inventory"]["snapshot"] = {
        "path": "output/latest.json",
        "status": "HOLD_SOURCE_NOT_CAPTURED",
        "raw_provider_source_certified": False,
    }
    path.write_text(json.dumps(inv), encoding="utf-8")
    with pytest.raises(ValueError, match="NO_SOURCE_BYTES_VERIFIED"):
        check(tmp_path)


def test_empty_file_is_still_verifiable_bytes(tmp_path):
    source, path, inv = fixture(tmp_path)
    source.write_bytes(b"")
    inv["source_inventory"]["snapshot"]["byte_count"] = 0
    inv["source_inventory"]["snapshot"]["sha256"] = hashlib.sha256(b"").hexdigest()
    path.write_text(json.dumps(inv), encoding="utf-8")
    assert check(tmp_path)["verified_file_count"] == 1


def test_manifest_parent_symlink_outside_extraction_root_is_rejected(tmp_path):
    root = tmp_path / "download"
    root.mkdir()
    fixture(root)
    manifest_dir = root / "output/sky_quickscan_information"
    outside = tmp_path / "external_manifest_dir"
    manifest_dir.rename(outside)
    manifest_dir.symlink_to(outside, target_is_directory=True)
    # Only the parent directory is a link; the leaf manifest is not.
    # Earlier is_file()+is_symlink() checks alone incorrectly accepted it.
    assert (manifest_dir / "same_run_source_inventory.json").is_file()
    assert not (manifest_dir / "same_run_source_inventory.json").is_symlink()
    with pytest.raises(ValueError, match="INVENTORY_MISSING_OR_UNSAFE_PATH"):
        check(root)
