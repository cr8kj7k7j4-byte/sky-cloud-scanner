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

    def test_unrelated_evidence_ledger_is_allowed(self):
        self.track("research/forward_event_ledger.py", "def read(): return None\n")
        self.assertTrue(check(self.root)["passed"])

    def test_retired_order_ledger_path_is_rejected(self):
        self.track("src/paper_trading.py", "def write_order(): pass\n")
        self.assertFalse(check(self.root)["passed"])

    def test_retired_import_is_rejected(self):
        self.track("src/consumer.py", "from src.paper_trading import write_order\n")
        self.assertFalse(check(self.root)["passed"])


if __name__ == "__main__":
    unittest.main()
