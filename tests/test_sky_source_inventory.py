"""Offline W0 manifest contract tests; zero Fugle/API, no trade."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.sky_source_inventory import build_inventory
from src.sky_same_run_artifact_verify import verify_downloaded_inventory

SHA = "a" * 40


class SameRunPostmarketInventoryTests(unittest.TestCase):
    def make(self, root, mode="postmarket_observation"):
        return build_inventory(base=root, run_id="123", attempt="1",
                               sha=SHA, event="workflow_dispatch", mode=mode)

    def test_present_postmarket_full_universe_hash_verified_by_existing_reader(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "output/sky_quickscan_information/full_universe.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"schema": "OBSERVATION", "checked_at_tpe":
                                        "2026-11-26T13:40:00+08:00"}))
            inventory = self.make(root)
            entry = inventory["source_inventory"]["full_market_reference"]
            self.assertEqual(entry["status"], "FILE_PRESENT_NOT_SOURCE_CERTIFIED")
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(entry["raw_provider_source_certified"])
            (path.parent / "same_run_source_inventory.json").write_text(json.dumps(inventory))
            result = verify_downloaded_inventory(root, expected_run_id="123",
                       expected_attempt="1", expected_head_sha=SHA, artifact_id=999)
            self.assertEqual(result["verified_file_count"], 1)
            self.assertFalse(result["provider_data_certified"])

    def test_missing_source_does_not_claim_verified_data(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self.make(root)
            self.assertEqual(manifest["source_inventory"]["full_market_reference"]
                             ["status"], "HOLD_SOURCE_NOT_CAPTURED")
            target = root / "output/sky_quickscan_information/same_run_source_inventory.json"
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "NO_SOURCE_BYTES_VERIFIED"):
                verify_downloaded_inventory(root, expected_run_id="123",
                    expected_attempt="1", expected_head_sha=SHA, artifact_id=999)

    def test_corrupt_json_stays_on_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "output/sky_quickscan_information/full_universe.json"
            p.parent.mkdir(parents=True)
            p.write_text("not json")
            entry = self.make(root)["source_inventory"]["full_market_reference"]
            self.assertEqual(entry["status"], "HOLD_INVALID_JSON")
            self.assertFalse(entry["raw_provider_source_certified"])

    def test_both_modes_same_contract_without_duplicate_controller(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            day = self.make(root, mode="intraday")
            post = self.make(root, mode="postmarket_observation")
            self.assertEqual(set(day["source_inventory"]), set(post["source_inventory"]))
            self.assertEqual(day["schema"], post["schema"])
            self.assertFalse(day["production_eligible"])
            self.assertFalse(post["production_eligible"])
            self.assertEqual(post["trade_action"], "禁止交易")

    def test_invalid_run_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "INVALID_GITHUB_RUN_PROVENANCE"):
                build_inventory(base=Path(td), run_id="bad", attempt="1",
                                sha=SHA, event="push", mode="postmarket_observation")


if __name__ == "__main__":
    unittest.main()
