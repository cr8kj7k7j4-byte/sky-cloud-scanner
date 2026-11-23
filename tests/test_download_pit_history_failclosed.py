"""Zero-paid PIT history fail-closed contract tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research import download_pit_history


class PITDownloadFailClosedTests(unittest.TestCase):
    def run_case(self, symbols, failed):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"sample": [
                {"symbol": s, "history_required_from": "2026-01-01",
                 "history_required_to": "2026-01-02"} for s in symbols
            ]}), encoding="utf-8")
            argv = ["download_pit_history.py", "--manifest", str(manifest),
                    "--out", str(root / "history")]
            def fake_hist(symbol, start, end):
                if symbol in failed:
                    raise RuntimeError("MOCK_DUPLICATE_CLAIM_BLOCKED")
                return [{"close": 100}]
            with patch.object(sys, "argv", argv), patch.object(
                    download_pit_history, "get_hist", side_effect=fake_hist):
                if failed or not symbols:
                    with self.assertRaisesRegex(SystemExit, "PIT_HISTORICAL_DOWNLOAD_INCOMPLETE"):
                        download_pit_history.main()
                else:
                    download_pit_history.main()
            rows = json.loads((root / "pit_history_download_summary.json").read_text())
            self.assertEqual(len(rows), len(symbols))
            return rows

    def test_all_success(self):
        self.assertTrue(all(row["ok"] for row in self.run_case(["2330", "2317"], set())))

    def test_partial_failure(self):
        rows = self.run_case(["2330", "2317"], {"2317"})
        self.assertTrue(rows[0]["ok"])
        self.assertFalse(rows[1]["ok"])
        self.assertIn("MOCK_DUPLICATE_CLAIM_BLOCKED", rows[1]["error"])

    def test_all_failed(self):
        self.assertFalse(self.run_case(["2330"], {"2330"})[0]["ok"])

    def test_empty_manifest(self):
        self.assertEqual(self.run_case([], set()), [])


if __name__ == "__main__":
    unittest.main()
