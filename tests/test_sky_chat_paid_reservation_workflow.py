"""Research-only paid API safety wiring regression: no provider call before claim verification."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/sky-chat-bridge.yml"


class PaidReservationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_scanner_comes_after_uploaded_verified_reservation(self):
        source = self.source
        reserve = source.index("python -m research.sky_paid_fugle_api_guard --scope 'sky:live:wholemarket'")
        upload = source.index("name: Publish reservation before any paid request")
        verify = source.index("name: Verify reservation ZIP independently (fail closed)")
        paid = source.index("name: Run read-only paid Fugle observations")
        self.assertLess(reserve, upload)
        self.assertLess(upload, verify)
        self.assertLess(verify, paid)
        self.assertIn("if: steps.guard.outputs.allowed == 'true' && steps.verify_claim.outcome == 'success'", source)
        self.assertIn("if: steps.guard.outputs.allowed == 'true' && steps.claim.outcome == 'success'", source)
        self.assertIn("name: ${{ steps.guard.outputs.claim_name }}", source)

    def test_shared_serialization_and_no_order_promotion(self):
        source = self.source
        self.assertIn("group: sky-fugle-paid-global-research-v1-live-wholemarket", source)
        self.assertIn("cancel-in-progress: false", source)
        self.assertIn("SKY_FUGLE_ONLY_MARKETDATA: '1'", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("gh api --method PUT", source)
        self.assertNotIn("schedule:", source)
        self.assertIn("sky-chat-${{ github.run_id }}", source)
        self.assertIn("sky-chat-external-readback-${{ github.run_id }}", source)


if __name__ == "__main__":
    unittest.main()
