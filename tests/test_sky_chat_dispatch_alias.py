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
        r"      - name: Run read-only paid Fugle", workflow, re.S
    )
    if match is None:
        raise AssertionError("DISPATCH_PRE_BRIDGE_STEP_MISSING")
    return "\n".join(line[10:] if line.startswith("          ") else line
                     for line in match.group(1).splitlines())


class DispatchAliasContractTests(unittest.TestCase):
    def test_dispatch_inputs_are_optional_and_keep_existing_push_working(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("branches: [main]", text)
        self.assertIn("inputs.command != 'use_saved_request'", text)
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


if __name__ == "__main__":
    unittest.main()
