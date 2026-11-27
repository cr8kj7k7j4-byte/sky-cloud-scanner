"""Prevent protected-main writes from the on-demand, research-only chat bridge."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/sky-chat-bridge.yml"


class ChatBridgeWorkflowContractTests(unittest.TestCase):
    def test_research_bridge_never_pushes_to_protected_main(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        # Shared atomic Git ref claims need write permission; direct main writes remain forbidden.
        self.assertIn("contents: write", workflow)
        self.assertIn("format('sky-alert-readonly-{0}', github.event.comment.id)", workflow)
        self.assertIn("|| 'sky-fugle-paid-global-research-v1-live-wholemarket'", workflow)
        self.assertIn("SKY_FUGLE_MONTHLY_RATE_CONTROL: '1'", workflow)
        self.assertIn("--monthly-rate-limited", workflow)
        self.assertIn("steps.verify_claim.outcome == 'success'", workflow)
        self.assertNotIn("gh api --method PUT", workflow)
        self.assertNotIn("git push", workflow)

    def test_status_is_preserved_in_same_run_artifact(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("name: sky-chat-${{ github.run_id }}", workflow)
        self.assertIn("output/chat_bridge/latest.json", workflow)
        self.assertIn("output/sky_quickscan_information/latest_13col.json", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn("retention-days: 90", workflow)

    def test_no_paid_scan_or_trading_schedule_added(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertIn("SKY_FUGLE_ONLY_MARKETDATA: '1'", workflow)


if __name__ == "__main__":
    unittest.main()
