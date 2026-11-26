"""Historical downloaded Artifact research contract tests; no API or orders."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.sky_historical_research_readback import read_complete_session_research

SHA = "a" * 40
DATE = "2026-11-26"


def fixture(root: Path):
    source = root / "output/sky_quickscan_information/full_universe.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
        "checked_at_tpe": "2026-11-26T13:40:00+08:00",
        "universe_count": 1,
        "observed_price_count": 1,
        "fresh_executed_count": 0,
        "all_symbols": [{
            "symbol": "1101", "name": "台泥",
            "source": "Fugle paid bulk snapshot",
            "snapshot_source_date": DATE,
            "snapshot_observed_at": "2026-11-26T13:40:00+08:00",
            "data_status": "UNVERIFIED_EXECUTION_TIME",
            "last_price": 31.2, "open_price": 31, "high_price": 32,
            "low_price": 30,
        }],
    }
    raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
    source.write_bytes(raw)
    manifest = root / "output/sky_quickscan_information/same_run_source_inventory.json"
    inventory = {
        "schema": "SKY_W0_SAME_RUN_SOURCE_INVENTORY_V1",
        "run_id": "123", "run_attempt": "2", "head_sha": SHA,
        "production_eligible": False, "trade_action": "禁止交易",
        "source_inventory": {
            "full_market_reference": {
                "path": "output/sky_quickscan_information/full_universe.json",
                "status": "FILE_PRESENT_NOT_SOURCE_CERTIFIED",
                "raw_provider_source_certified": False,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        },
    }
    manifest.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
    return source, manifest, report, inventory


def read(root, **override):
    args = {
        "expected_run_id": "123", "expected_attempt": "2",
        "expected_head_sha": SHA, "artifact_id": 456,
        "verified_complete_session_date": DATE,
        "calendar_session_certified": True,
    }
    args.update(override)
    return read_complete_session_research(root, **args)


class HistoricalResearchReadbackTests(unittest.TestCase):
    def test_valid_same_run_history_is_only_research(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            got = read(root)
            self.assertEqual(got["status"], "HISTORICAL_BYTES_READABLE_RESEARCH_ONLY")
            self.assertEqual(got["universe_count"], 1)
            self.assertEqual(got["run_id"], "123")
            self.assertIn("台泥", got["research_markdown"])
            self.assertIn("觀察價 31.20，未驗證", got["research_markdown"])
            self.assertFalse(got["source_certified"])
            self.assertFalse(got["new_entry_authorized"])
            self.assertEqual(got["trade_action"], "禁止交易")

    def test_unverified_official_calendar_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            with self.assertRaisesRegex(ValueError, "OFFICIAL_SESSION_NOT_CERTIFIED"):
                read(root, calendar_session_certified=False)

    def test_old_session_or_mismatched_label_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            with self.assertRaisesRegex(ValueError, "HISTORICAL_SOURCE_SESSION_MISMATCH"):
                read(root, verified_complete_session_date="2026-11-25")

    def test_next_day_capture_keeps_prior_verified_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, path, report, inventory = fixture(root)
            report["checked_at_tpe"] = "2026-11-27T05:01:00+08:00"
            report["all_symbols"][0]["snapshot_observed_at"] = "2026-11-27T05:00:00+08:00"
            raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
            source.write_bytes(raw)
            entry = inventory["source_inventory"]["full_market_reference"]
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["byte_count"] = len(raw)
            path.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
            got = read(root)
            self.assertEqual(got["source_session_date"], DATE)
            self.assertEqual(got["capture_date_tpe"], "2026-11-27")
            self.assertFalse(got["live_quote_certified"])
            self.assertFalse(got["new_entry_authorized"])

    def test_capture_before_verified_source_session_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, path, report, inventory = fixture(root)
            report["checked_at_tpe"] = "2026-11-25T20:00:00+08:00"
            raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
            source.write_bytes(raw)
            entry = inventory["source_inventory"]["full_market_reference"]
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["byte_count"] = len(raw)
            path.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HISTORICAL_CAPTURE_BEFORE_SESSION"):
                read(root)

    def test_row_observation_after_capture_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, path, report, inventory = fixture(root)
            report["all_symbols"][0]["snapshot_observed_at"] = "2026-11-27T05:01:00+08:00"
            raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
            source.write_bytes(raw)
            entry = inventory["source_inventory"]["full_market_reference"]
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["byte_count"] = len(raw)
            path.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HISTORICAL_ROW_CAPTURE_TIME_INVALID"):
                read(root)

    def test_missing_row_source_session_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, path, report, inventory = fixture(root)
            del report["all_symbols"][0]["snapshot_source_date"]
            raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
            source.write_bytes(raw)
            entry = inventory["source_inventory"]["full_market_reference"]
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["byte_count"] = len(raw)
            path.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HISTORICAL_SOURCE_SESSION_MISMATCH"):
                read(root)

    def test_tampered_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _, _, _ = fixture(root)
            source.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_DIGEST_MISMATCH"):
                read(root)

    def test_missing_complete_market_reference_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, path, _, inv = fixture(root)
            inv["source_inventory"]["full_market_reference"]["status"] = "HOLD_INVALID_JSON"
            path.write_text(json.dumps(inv), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "FULL_MARKET_REFERENCE_NOT_VERIFIED"):
                read(root)

    def test_malformed_and_duplicate_symbols_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, path, report, inv = fixture(root)
            report["all_symbols"].append(report["all_symbols"][0].copy())
            report["universe_count"] = 2
            raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
            source.write_bytes(raw)
            entry = inv["source_inventory"]["full_market_reference"]
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["byte_count"] = len(raw)
            path.write_text(json.dumps(inv), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "INVALID_OR_DUPLICATE_HISTORICAL_SYMBOL"):
                read(root)


if __name__ == "__main__":
    unittest.main()
