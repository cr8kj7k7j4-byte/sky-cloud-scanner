import json
import tempfile
import unittest
from pathlib import Path
from src.scan_history_archive import make_record


class ScanHistoryArchiveTests(unittest.TestCase):
    def test_missing_result_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = make_record(tmp, "123", "1")
            self.assertEqual(record["status"], "DATA_BLOCKED")
            self.assertEqual(record["candidates"], [])
            self.assertFalse(record["production_signal"])

    def test_unverified_coverage_cannot_be_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "latest.json").write_text(json.dumps({
                "market_data_gate": "PASS_FULL_MARKET_LIVE",
                "operational_full_market_scan": True,
                "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
                "live_market_evidence": {"valid_whole_market_operational": False},
                "candidates": [{"symbol": "1101"}]
            }), encoding="utf-8")
            record = make_record(tmp, "123", "1")
            self.assertEqual(record["status"], "DATA_BLOCKED")
            self.assertEqual(record["candidate_count"], 1)

    def test_valid_full_market_evidence_only_marks_market_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "latest.json").write_text(json.dumps({
                "market_data_gate": "PASS_FULL_MARKET_LIVE",
                "operational_full_market_scan": True,
                "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
                "live_market_evidence": {"valid_whole_market_operational": True},
                "candidates": []
            }), encoding="utf-8")
            record = make_record(tmp, "123", "1")
            self.assertEqual(record["status"], "MARKET_DATA_VERIFIED")
            self.assertFalse(record["production_signal"])


if __name__ == "__main__":
    unittest.main()
