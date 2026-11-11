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
