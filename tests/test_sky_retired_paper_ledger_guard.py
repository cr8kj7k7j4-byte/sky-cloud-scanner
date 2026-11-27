"""Regression tests for retired simulated-trading ledger guard (offline)."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from research.sky_retired_paper_ledger_guard import check


class RetiredPaperLedgerGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def track(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        subprocess.run(["git", "add", name], cwd=self.root, check=True)

    def test_analysis_only_policy_never_requires_retired_paper_ledger(self):
        policy = (Path(__file__).resolve().parents[1] /
                  "docs/SKY_NO_BROKER_ACCOUNT_RESEARCH_POLICY_V1.md").read_text(
                      encoding="utf-8")
        self.assertIn("RESEARCH_AVAILABLE", policy)
        self.assertIn("OBSERVATION_ONLY", policy)
        self.assertIn("P0-R", policy)
        self.assertIn("NO_TRADE", policy)
        self.assertIn("永久禁止", policy)
        self.assertNotIn("PAPER_INPUT_REQUIRED", policy)
        self.assertNotIn("P0-R 研究／PAPER_ONLY", policy)

    def test_unrelated_evidence_ledger_is_allowed(self):
        self.track("research/forward_event_ledger.py", "def read(): return None\n")
        self.assertTrue(check(self.root)["passed"])

    def test_retired_order_ledger_path_is_rejected(self):
        self.track("src/paper_trading.py", "def write_order(): pass\n")
        self.assertFalse(check(self.root)["passed"])

    def test_retired_import_is_rejected(self):
        self.track("src/consumer.py", "from src.paper_trading import write_order\n")
        self.assertFalse(check(self.root)["passed"])


    def test_legacy_w6_manual_collector_requires_fail_closed_job(self):
        path = ".github/workflows/w6-forward-execution-evidence.yml"
        safe = ("name: Legacy W6\n"
                "on:\n  workflow_dispatch:\n"
                "jobs:\n  collect-and-report:\n"
                "    if: ${{ false }}\n"
                "    runs-on: ubuntu-latest\n")
        self.track(path, safe)
        self.assertTrue(check(self.root)["passed"])

    def test_legacy_w6_without_guard_is_rejected(self):
        path = ".github/workflows/w6-forward-execution-evidence.yml"
        self.track(path, "on:\n  workflow_dispatch:\njobs:\n  collect-and-report:\n    runs-on: ubuntu-latest\n")
        result = check(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("RETIRED_W6_COLLECTOR_NOT_FAIL_CLOSED",
                      [v["reason"] for v in result["violations"]])

    def test_legacy_w6_added_job_is_rejected(self):
        path = ".github/workflows/w6-forward-execution-evidence.yml"
        self.track(path, ("jobs:\n  collect-and-report:\n    if: ${{ false }}\n"
                          "  alternate-job:\n    runs-on: ubuntu-latest\n"))
        self.assertFalse(check(self.root)["passed"])


if __name__ == "__main__":
    unittest.main()
