"""Exercise the exact inline diagnostic guard shipped in the Actions workflow."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sky-chat-bridge.yml"
RUN_ID = "123456789"


class WorkflowGuardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"      - name: Verify status and preserve a failed-run diagnostic\n"
            r".*?          python - <<'PY'\n"
            r"(.*?)\n          PY\n"
            r"      - name: Upload complete",
            raw,
            re.S,
        )
        if not match:
            raise AssertionError("Diagnostic step not found in Actions workflow")
        cls.guard = "\n".join(
            line[10:] if line.startswith("          ") else line
            for line in match.group(1).splitlines()
        )

    def run_guard(self, payload, bridge_outcome="success"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "output/chat_bridge/latest.json"
            if payload is not ...:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
            env = dict(os.environ, GITHUB_RUN_ID=RUN_ID, BRIDGE_OUTCOME=bridge_outcome)
            result = subprocess.run(
                [sys.executable, "-c", self.guard],
                cwd=root, env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertTrue(target.exists(), result.stderr)
            diagnostic = json.loads(target.read_text(encoding="utf-8"))
            self.assertIs(diagnostic["production_eligible"], False)
            self.assertIs(diagnostic["automatic_order"], False)
            return result, diagnostic

    def test_missing_status_writes_diagnostic_and_fails(self):
        result, status = self.run_guard(...)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(status["status"], "FAILED_NO_VALID_STATUS")

    def test_json_null_writes_diagnostic_and_fails(self):
        result, status = self.run_guard(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(status["status"], "FAILED_NO_VALID_STATUS")

    def test_stale_run_id_is_rejected(self):
        data = self.good_status()
        data["scan_id"] = "old"
        result, status = self.run_guard(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(status["status"], "FAILED_NO_VALID_STATUS")

    def test_empty_observations_fail(self):
        data = self.good_status()
        data["observed_price_count"] = 0
        result, status = self.run_guard(data)
        self.assertNotEqual(result.returncode, 0)

    def test_prior_failed_scan_remains_failed(self):
        data = self.good_status()
        data["status"] = "DATA_BLOCKED_NO_OBSERVATIONS"
        result, status = self.run_guard(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(status["status"], "DATA_BLOCKED_NO_OBSERVATIONS")

    def test_failed_runner_must_fail_even_with_good_report(self):
        result, status = self.run_guard(self.good_status(), "failure")
        self.assertNotEqual(result.returncode, 0)

    def test_valid_research_status_passes_only_as_research(self):
        result, status = self.run_guard(self.good_status())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(status["status"], "REPORT_READY_RESEARCH_ONLY")

    @staticmethod
    def good_status():
        return {
            "schema": "SKY_CHAT_SCAN_STATUS_V1",
            "scan_id": RUN_ID,
            "status": "REPORT_READY_RESEARCH_ONLY",
            "row_count": 2,
            "observed_price_count": 2,
            "data_timestamp": "2026-11-10T13:20:00+08:00",
            "source": "FUGLE_PAID_SNAPSHOT",
            "production_eligible": False,
            "automatic_order": False,
        }


if __name__ == "__main__":
    unittest.main()
