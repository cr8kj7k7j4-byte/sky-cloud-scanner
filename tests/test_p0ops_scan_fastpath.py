"""Regression tests for intraday scanner fast path; no network or broker calls."""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/scan.yml")


def workflow_text():
    return WORKFLOW.read_text(encoding="utf-8")


def step(text, name):
    pattern = r"(?ms)^      - name: " + re.escape(name) + r"\n.*?(?=^      - (?:name:|uses:)|\Z)"
    m = re.search(pattern, text)
    if m is None:
        raise AssertionError(f"Missing workflow step: {name}")
    return m.group(0)


class TestFastPath(unittest.TestCase):
    def test_original_schedule_remains_exact(self):
        text = workflow_text()
        self.assertIn('cron: "5,15,30,50 1 * * 1-5"', text)
        self.assertIn('cron: "15 2 * * 1-5"', text)
        self.assertIn("python -m src.trading_calendar", text)

    def test_scanner_runs_original_source_and_preserves_hard_gates(self):
        text = workflow_text()
        scan = step(text, "Run scanner")
        self.assertIn('"-m", "src.main"', scan)
        for token in ('STRICT_OFFICIAL_MODE: "1"', 'ACCOUNT_EQUITY:', 'RISK_PER_TRADE_PCT:', 'DAILY_LOSS_LIMIT_PCT:', 'MAX_PORTFOLIO_HEAT_PCT:', 'CONSECUTIVE_LOSSES:'):
            self.assertIn(token, scan)
        verify = step(text, "Verify operational market coverage")
        for token in ('valid_whole_market_operational', 'WHOLE_MARKET_EXECUTED_LIVE', 'PASS_FULL_MARKET_LIVE', 'raise SystemExit'):
            self.assertIn(token, verify)

    def test_diagnosis_is_not_in_success_critical_path(self):
        text = workflow_text()
        scan = step(text, "Run scanner")
        verify = step(text, "Verify operational market coverage")
        diagnosis = step(text, "Diagnose sources on scanner or coverage failure")
        self.assertLess(text.index(scan), text.index(verify))
        self.assertLess(text.index(verify), text.index(diagnosis))
        self.assertIn("&& failure()", diagnosis)
        self.assertIn("continue-on-error: true", diagnosis)
        self.assertNotIn("Diagnose data sources", text)

    def test_failed_scanner_preserves_failure_and_diagnostic_artifacts(self):
        text = workflow_text()
        scan = step(text, "Run scanner")
        self.assertIn("sys.exit(proc.returncode)", scan)
        self.assertIn("scan_runtime.json", scan)
        self.assertIn("time.monotonic()", scan)
        self.assertIn('if: always()', step(text, "Upload scan report"))
        self.assertIn("if: failure()", step(text, "Notify Telegram when intraday scan fails"))
        self.assertIn("python research/intraday_scan_failure_alert.py", step(text, "Notify Telegram when intraday scan fails"))

    def test_no_trading_or_promotion_added(self):
        text = workflow_text()
        self.assertNotIn("submit_order", text)
        self.assertNotIn("merge_pull_request", text)
        self.assertNotIn("PROMOTE_CANDIDATE", text)


if __name__ == "__main__":
    unittest.main()
