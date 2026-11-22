"""W0 anti-duplicate static workflow contracts; no network, paid API, or orders."""
import tempfile
import unittest
from pathlib import Path

from scripts.sky_workflow_dedup_audit import audit, workflow_info, SCAN_CRONS


def workflow(name, crons=(), *, main=False):
    cron_lines = "".join(f"    - cron: '{c}'\n" for c in crons)
    body = "name: Test\non:\n  workflow_dispatch:\n"
    if crons:
        body += "  schedule:\n" + cron_lines
    body += "jobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n"
    body += "      - run: " + ("python -m src.main" if main else "echo noop") + "\n"
    return body


class WorkflowDedupAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "scan.yml").write_text(workflow("scan.yml", SCAN_CRONS, main=True), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_canonical_scan_is_accepted(self):
        result = audit(self.root)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["scheduled_workflows"], 1)

    def test_no_false_schedule_from_comment(self):
        path = self.root / "other.yml"
        path.write_text(
            "# schedule:\n" + workflow("other.yml").replace(
                "  workflow_dispatch:", "  workflow_dispatch:\n  # schedule:\n  #   - cron: '5,15,30,50 1 * * 1-5'"
            ), encoding="utf-8",
        )
        self.assertFalse(workflow_info(path)["active_schedule"])
        self.assertEqual(audit(self.root)["failures"], [])

    def test_duplicate_canonical_cron_blocks(self):
        (self.root / "copy.yml").write_text(workflow("copy.yml", [SCAN_CRONS[0]]), encoding="utf-8")
        self.assertIn("DUPLICATE_CANONICAL_SCAN_CRON:copy.yml", audit(self.root)["failures"])

    def test_second_scheduled_main_scanner_blocks(self):
        (self.root / "copy.yml").write_text(workflow("copy.yml", ["10 1 * * 1-5"], main=True), encoding="utf-8")
        self.assertIn("DUPLICATE_SCHEDULED_MAIN_SCANNER:copy.yml", audit(self.root)["failures"])

    def test_maintain_paid_five_minute_dispatch_pause(self):
        (self.root / "sky-full-market-five-minute-dispatch.yml").write_text(
            workflow("sky-full-market-five-minute-dispatch.yml", ["*/5 1-5 * * 1-5"]),
            encoding="utf-8",
        )
        self.assertIn("PAID_FIVE_MIN_DISPATCH_REACTIVATED", audit(self.root)["failures"])

    def test_unrelated_shared_cron_is_review_only(self):
        for name in ("a.yml", "b.yml"):
            (self.root / name).write_text(workflow(name, ["30 8 * * 1-5"]), encoding="utf-8")
        result = audit(self.root)
        self.assertEqual(result["failures"], [])
        self.assertEqual(len(result["shared_crons_review_only"]), 1)


if __name__ == "__main__":
    unittest.main()
