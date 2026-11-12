import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from research.sky_paid_fugle_api_inventory import audit, cohort, triggers


class PaidWorkflowInventoryTests(unittest.TestCase):
    def test_commented_schedule_does_not_count(self):
        src = """name: Sample
on:
  # schedule:
  # - cron: '*/5 * * * *'
  workflow_dispatch:
jobs:
  observe:
    runs-on: ubuntu-latest
"""
        self.assertFalse(triggers(src)["schedule"])
        self.assertTrue(triggers(src)["workflow_dispatch"])

    def test_active_schedule_counts_only_in_on_block(self):
        src = """on:
  schedule:
    - cron: '* * * * *'
jobs:
  scan:
    steps:
      - run: 'echo schedule:'
"""
        self.assertTrue(triggers(src)["schedule"])

    def test_filename_cohort_is_non_authoritative(self):
        self.assertEqual(cohort("w3a-full-pit-history-export.yml"), "HISTORICAL_DATA_OR_BACKTEST")
        self.assertEqual(cohort("sky-selected-quote-view.yml"), "LIVE_MARKET_OR_SCAN")

    def test_artifact_guard_cannot_be_misreported_as_atomic_endpoint_gate(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "fugle.yml"
            p.write_text(
                """on:
  workflow_dispatch:
concurrency:
  group: sky-fugle-paid-global-research-v1
jobs:
  observe:
    steps:
      - env:
          FUGLE_API_KEY: ${{ secrets.FUGLE_API_KEY }}
      - run: python -m research.sky_paid_fugle_api_guard --verify
""", encoding="utf-8")
            result = audit(Path(td))
            self.assertEqual(result["unguarded_candidate_count"], 0)
            self.assertEqual(result["atomic_endpoint_enforced_workflow_count"], 0)
            self.assertEqual(result["repository_wide_acceptance"], "HOLD")

    def test_real_repository_reports_wiring_but_no_runtime_promotion(self):
        result = audit()
        self.assertGreaterEqual(result["secret_referencing_workflow_count"], 40)
        self.assertEqual(result["atomic_endpoint_code_wired_candidate_count"], 3)
        self.assertEqual(result["atomic_endpoint_isolated_broker_candidate_count"], 2)
        self.assertEqual(result["atomic_endpoint_enforced_workflow_count"], 0)
        self.assertEqual(result["repository_wide_acceptance"], "HOLD")

    def test_inventory_holds_when_any_unguarded_manual_entrypoint_exists(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "legacy.yml"
            p.write_text("""on:
  workflow_dispatch:
jobs:
  x:
    steps:
      - env:
          FUGLE_API_KEY: ${{ secrets.FUGLE_API_KEY }}
""")
            a = audit(Path(td))
            self.assertEqual(a["unguarded_candidate_count"], 1)
            self.assertEqual(a["unguarded_schedule_enabled_count"], 0)
            self.assertEqual(a["unguarded_manual_or_event_count"], 1)
            self.assertEqual(a["repository_wide_acceptance"], "HOLD")


if __name__ == "__main__":
    unittest.main()
