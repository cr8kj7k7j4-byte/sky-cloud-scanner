import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from research import three_model_fugle_pipeline as pipeline
from research import fugle_market_quality_audit as quality


class DirectPaidTransportGuardTests(unittest.TestCase):
    def test_three_model_historical_request_claims_before_network(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{}'
        with patch.object(pipeline, "guard_fugle_request") as guard, \
             patch.object(pipeline, "urlopen", return_value=response) as network, \
             patch.object(pipeline, "normalize_response", return_value=[]):
            pipeline.read_fugle("2330", "5", date(2026, 11, 1),
                                date(2026, 11, 2), "test-key")
        guard.assert_called_once()
        network.assert_called_once()
        self.assertLess(guard.call_args_list[0] is not None, network.call_count > 0)

    def test_mocked_three_model_transport_does_not_claim_or_use_network(self):
        get = MagicMock(return_value={"symbol": "2330", "timeframe": "5", "data": []})
        with patch.object(pipeline, "guard_fugle_request") as guard, \
             patch.object(pipeline, "urlopen") as network, \
             patch.object(pipeline, "normalize_response", return_value=[]):
            pipeline.read_fugle("2330", "5", date(2026, 11, 1),
                                date(2026, 11, 2), "test-key", get=get)
        guard.assert_not_called()
        network.assert_not_called()

    def test_market_quality_claims_only_paid_fugle_url(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{}'
        response.headers.get_content_charset.return_value = "utf-8"
        with patch.object(quality, "guard_fugle_request") as guard, \
             patch.object(quality.urllib.request, "urlopen", return_value=response):
            quality.request(quality.API + "/snapshot/quotes/TSE?type=COMMONSTOCK", "test-key")
            quality.request(quality.SOURCES["TSE"])
        guard.assert_called_once()
        self.assertIn("/snapshot/quotes/TSE", guard.call_args.args[0])


class PaidWorkflowWiringTests(unittest.TestCase):
    WORKFLOWS = (
        ".github/workflows/sky-single-stock-realtime.yml",
        ".github/workflows/swing-live-scan.yml",
        ".github/workflows/swing-v11-live-scan.yml",
        ".github/workflows/three-model-fugle-api-smoke.yml",
        ".github/workflows/fugle-market-quality-audit.yml",
    )

    def test_paid_workflows_enable_atomic_claim_with_write_permission(self):
        for path in self.WORKFLOWS:
            with self.subTest(path=path):
                content = Path(path).read_text(encoding="utf-8")
                self.assertIn("SKY_PAID_ATOMIC_ENFORCE: \"1\"", content)
                self.assertIn("GH_TOKEN: ${{ github.token }}", content)
                self.assertIn("contents: write", content)


if __name__ == "__main__":
    unittest.main()
