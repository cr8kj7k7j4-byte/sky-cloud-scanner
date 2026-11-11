"""Offline verification of the existing workflow_dispatch -> Sky Bridge request route."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.sky_scan_readback import COMMANDS

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sky-chat-bridge.yml"


def dispatch_code():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(
        r"      - name: Apply safe optional dispatch alias.*?\n"
        r"        run: \|\n"
        r"          python - <<'PY'\n"
        r"(.*?)\n          PY\n"
        r"(?=      - name: )", workflow, re.S
    )
    if match is None:
        raise AssertionError("DISPATCH_PRE_BRIDGE_STEP_MISSING")
    # A required paid reservation can appear between safe request routing and
    # the existing bridge. Ensure aliases cannot bypass that reservation.
    assert workflow.index("Apply safe optional dispatch alias") < workflow.index("Reserve shared Fugle paid API slot")
    assert workflow.index("Verify reservation ZIP content independently") < workflow.index("Run read-only paid Fugle observations")
    assert "steps.verify_claim.outcome == 'success'" in workflow
    return "\n".join(line[10:] if line.startswith("          ") else line
                     for line in match.group(1).splitlines())


class DispatchAliasContractTests(unittest.TestCase):
    def test_dispatch_inputs_are_optional_and_keep_existing_push_working(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("branches: [main]", text)
        self.assertIn("inputs.command != 'use_saved_request'", text)
        self.assertIn("inputs.command != '' && inputs.command != 'use_saved_request'", text)
        self.assertIn("SKY_DISPATCH_COMMAND: ${{ inputs.command }}", text)
        self.assertIn("SKY_DISPATCH_REQUEST_ID: ${{ inputs.request_id }}", text)
        self.assertIn("read_only_no_orders", text)
        self.assertIn("type: choice", text)
        for alias in COMMANDS:
            self.assertIn("- '" + alias + "'", text)

    def test_each_alias_reaches_saved_request_file_before_existing_bridge(self):
        code = dispatch_code()
        for alias in sorted(COMMANDS):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                (tmp / "scan_requests/chat").mkdir(parents=True)
                env = dict(os.environ, PYTHONPATH=str(ROOT),
                           GITHUB_RUN_ID="987654321",
                           SKY_DISPATCH_COMMAND=alias,
                           SKY_DISPATCH_REQUEST_ID="chat-dispatch-test-987654321")
                executed = subprocess.run([sys.executable, "-c", code], cwd=tmp,
                                          env=env, capture_output=True, text=True)
                self.assertEqual(executed.returncode, 0, executed.stderr)
                payload = json.loads((tmp / "scan_requests/chat/latest.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["command"], alias)
                self.assertEqual(payload["request_id"], "chat-dispatch-test-987654321")
                self.assertIs(payload["read_only_no_orders"], True)

    def test_blank_request_id_generates_unique_run_id(self):
        code = dispatch_code()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "scan_requests/chat").mkdir(parents=True)
            env = dict(os.environ, PYTHONPATH=str(ROOT), GITHUB_RUN_ID="987654322",
                       SKY_DISPATCH_COMMAND="Sky 快掃", SKY_DISPATCH_REQUEST_ID="")
            executed = subprocess.run([sys.executable, "-c", code], cwd=tmp,
                                      env=env, capture_output=True, text=True)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            payload = json.loads((tmp / "scan_requests/chat/latest.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["request_id"], "chat-dispatch-987654322")

    def test_invalid_alias_fails_closed_without_writing_request(self):
        code = dispatch_code()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "scan_requests/chat").mkdir(parents=True)
            env = dict(os.environ, PYTHONPATH=str(ROOT), GITHUB_RUN_ID="987654323",
                       SKY_DISPATCH_COMMAND="unsupported buy now",
                       SKY_DISPATCH_REQUEST_ID="chat-invalid-987654323")
            executed = subprocess.run([sys.executable, "-c", code], cwd=tmp,
                                      env=env, capture_output=True, text=True)
            self.assertNotEqual(executed.returncode, 0)
            self.assertFalse((tmp / "scan_requests/chat/latest.json").exists())

    def test_paid_reservation_denial_is_reported_as_fail_closed(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        segment = workflow.split("      - name: Verify status and preserve a failed-run diagnostic", 1)[1]
        segment = segment.split("      - name: Upload complete 13-column report and status", 1)[0]
        match = re.search(r"          python - <<'PY'\\n(.*?)\\n          PY", segment, re.S)
        self.assertIsNotNone(match)
        code = "\\n".join(line[10:] if line.startswith("          ") else line
                         for line in match.group(1).splitlines())
        scenarios = [
            ({"GUARD_OUTCOME": "success", "GUARD_ALLOWED": "false"},
             "DATA_BLOCKED_PAID_API_RESERVATION", "PAID_API_RESERVATION_DENIED"),
            ({"GUARD_OUTCOME": "failure"},
             "DATA_BLOCKED_PAID_API_GUARD", "PAID_API_GUARD_ERROR"),
            ({"GUARD_OUTCOME": "success", "GUARD_ALLOWED": "true", "CLAIM_OUTCOME": "failure"},
             "DATA_BLOCKED_PAID_API_RESERVATION", "PAID_API_RESERVATION_UPLOAD_FAILED"),
            ({"GUARD_OUTCOME": "success", "GUARD_ALLOWED": "true",
              "CLAIM_OUTCOME": "success", "VERIFY_CLAIM_OUTCOME": "failure"},
             "DATA_BLOCKED_PAID_API_RESERVATION", "PAID_API_RESERVATION_READBACK_FAILED"),
        ]
        for overrides, expected_status, expected_reason in scenarios:
            with self.subTest(expected_reason=expected_reason), tempfile.TemporaryDirectory() as td:
                env = dict(os.environ, GITHUB_RUN_ID="987654324", BRIDGE_OUTCOME="skipped",
                           GUARD_OUTCOME="skipped", GUARD_ALLOWED="",
                           CLAIM_OUTCOME="skipped", VERIFY_CLAIM_OUTCOME="skipped")
                env.update(overrides)
                proc = subprocess.run([sys.executable, "-c", code], cwd=td,
                                      env=env, capture_output=True, text=True)
                self.assertNotEqual(proc.returncode, 0)
                status = json.loads((Path(td) / "output/chat_bridge/latest.json").read_text(encoding="utf-8"))
                self.assertEqual(status["status"], expected_status)
                self.assertEqual(status["block_reason"], expected_reason)
                self.assertIs(status["production_eligible"], False)
                self.assertIs(status["automatic_order"], False)


if __name__ == "__main__":
    unittest.main()
