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


class LegacyPaidWorkflowW0GuardContracts(unittest.TestCase):
    """Offline proof that legacy manual paid entries cannot silently bypass W0."""

    def _workflow(self, name):
        return (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
                name).read_text(encoding="utf-8")

    def test_manual_paid_probes_require_atomic_claim_and_no_auto_push(self):
        for name in (
            "a-plan-live-market-validation.yml",
            "mcr-preopen-readiness.yml",
            "p0ops-provider-preflight.yml",
            "w3a-opening-acceleration-2026-jan-sep.yml",
            "w3a-opening-acceleration-2026-jan-oct22.yml",
        ):
            with self.subTest(workflow=name):
                content = self._workflow(name)
                self.assertIn("  workflow_dispatch:", content)
                self.assertNotRegex(content, r"(?m)^  push:")
                self.assertIn("SKY_PAID_ATOMIC_ENFORCE:", content)
                self.assertIn("GH_TOKEN:", content)
                self.assertIn("contents: write", content)

    def test_unprotected_pinned_historical_pilot_is_parked(self):
        content = self._workflow("ai-direction-pilot-once.yml")
        self.assertNotRegex(content, r"(?m)^  push:")
        self.assertIn("  workflow_dispatch:", content)
        self.assertIn("if: ${{ false }}", content)
        self.assertIn("legacy pinned SHA has no verified per-request atomic Claim", content)

    def test_real_claim_race_is_limited_to_pr689_and_two_existing_workflows(self):
        for name in ("governance-e2e-validation.yml",
                     "w3b-production-hardening.yml"):
            with self.subTest(workflow=name):
                content = self._workflow(name)
                self.assertIn("w0-cross-workflow-atomic-claim-proof:", content)
                self.assertIn("github.event.pull_request.number == 689", content)
                self.assertIn("sky_w0_cross_workflow_claim_evidence.py", content)
                self.assertIn("sky-w0-claim-race-", content)


if __name__ == "__main__":
    unittest.main()
