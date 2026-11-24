"""W0 anti-duplicate static workflow contracts; no network, paid API, or orders."""
import tempfile
import unittest
import shutil
from pathlib import Path

from scripts.sky_workflow_dedup_audit import audit, workflow_info, SCAN_CRONS, reuse_first_fallback_contract


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


    def test_reuse_first_static_contract_on_actual_repository(self):
        repo = Path(__file__).resolve().parents[1]
        result = reuse_first_fallback_contract(repo)
        self.assertEqual(result["failures"], [])
        self.assertTrue(all(result["checks"].values()))
        # Static contract never claims provider authorization or live E2E.
        self.assertFalse(result["live_fugle_entitlement_verified"])
        self.assertFalse(result["same_run_live_data_verified"])
        self.assertFalse(result["production_eligible"])

    def _copy_contract_fixture(self, destination):
        source = Path(__file__).resolve().parents[1]
        for relpath in reuse_first_fallback_contract(source)["checked_sources"].values():
            target = destination / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relpath, target)

    def test_missing_execution_gate_blocks_existing_governance_ci(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            self._copy_contract_fixture(repo)
            workflow = repo / ".github/workflows/scan.yml"
            workflow.write_text(
                workflow.read_text(encoding="utf-8").replace(
                    'EXEC_ENFORCE_GATE: "1"', 'EXEC_ENFORCE_GATE: "0"', 1
                ), encoding="utf-8"
            )
            self.assertIn(
                "REUSE_FIRST_CONTRACT_DRIFT:canonical_scan_execution_cost_gate",
                reuse_first_fallback_contract(repo)["failures"],
            )

    def test_claim_or_source_semantics_regression_blocks_governance(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            self._copy_contract_fixture(repo)
            claim_wf = repo / ".github/workflows/scan.yml"
            claim_wf.write_text(
                claim_wf.read_text(encoding="utf-8").replace(
                    "Independently verify paid reservation",
                    "Skip paid reservation verification",
                    1,
                ), encoding="utf-8"
            )
            candle = repo / "src/sky_v14_ticker_candles_probe.py"
            candle.write_text(
                candle.read_text(encoding="utf-8").replace(
                    '"bar_timestamp_semantics_certified":False',
                    '"bar_timestamp_semantics_certified":True',
                    1,
                ), encoding="utf-8"
            )
            failures = reuse_first_fallback_contract(repo)["failures"]
            self.assertIn("REUSE_FIRST_CONTRACT_DRIFT:single_paid_claim_before_scanner", failures)
            self.assertIn("REUSE_FIRST_CONTRACT_DRIFT:five_minute_provider_semantics_fail_closed", failures)

    def test_missing_required_canonical_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            self._copy_contract_fixture(repo)
            (repo / "research/sky_intraday_plan_a_two_track_acceptance.py").unlink()
            failures = reuse_first_fallback_contract(repo)["failures"]
            self.assertIn(
                "MISSING_CANONICAL_SOURCE:research/sky_intraday_plan_a_two_track_acceptance.py",
                failures,
            )


if __name__ == "__main__":
    unittest.main()
