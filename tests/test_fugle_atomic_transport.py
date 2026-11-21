import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from research import three_model_fugle_pipeline as pipeline
from research import fugle_market_quality_audit as quality
from research import fugle_2026_entitlement_probe as entitlement


class DirectPaidTransportGuardTests(unittest.TestCase):
    def test_three_model_historical_request_claims_before_network(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{}'
        order = []
        with patch.object(pipeline, "guard_fugle_request", side_effect=lambda *a: order.append("guard")) as guard, \
             patch.object(pipeline, "urlopen", side_effect=lambda *a, **k: (order.append("network"), response)[1]) as network, \
             patch.object(pipeline, "normalize_response", return_value=[]):
            pipeline.read_fugle("2330", "5", date(2026, 11, 1),
                                date(2026, 11, 2), "test-key")
        guard.assert_called_once()
        network.assert_called_once()
        self.assertEqual(order, ["guard", "network"])

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


class DirectPaidTransportGuardTests(unittest.TestCase):
    def test_entitlement_probe_claims_before_real_requests_transport(self):
        order = []
        response = MagicMock(status_code=403)
        with patch.object(entitlement, "guard_fugle_request", side_effect=lambda *a: order.append("guard")) as guard, \\
             patch("requests.get", side_effect=lambda *a, **k: (order.append("network"), response)[1]) as network:
            entitlement.run_probe("test-key", symbols=("2330",))
        guard.assert_called_once()
        network.assert_called_once()
        self.assertEqual(order, ["guard", "network"])

    def test_injected_entitlement_transport_stays_offline(self):
        response = MagicMock(status_code=403)
        with patch.object(entitlement, "guard_fugle_request") as guard:
            entitlement.run_probe("test-key", symbols=("2330",), get=lambda *a, **k: response)
        guard.assert_not_called()


class PaidWorkflowWiringTests(unittest.TestCase):
    WORKFLOWS = (
        ".github/workflows/sky-single-stock-realtime.yml",
        ".github/workflows/swing-live-scan.yml",
        ".github/workflows/swing-v11-live-scan.yml",
        ".github/workflows/three-model-fugle-api-smoke.yml",
        ".github/workflows/fugle-market-quality-audit.yml",
        ".github/workflows/three-model-fugle-private-ledger.yml",
        ".github/workflows/three-model-next-session-markout.yml",
        ".github/workflows/sky-market-provider-readiness.yml",
        ".github/workflows/sky-limited-candidate-research.yml",
        ".github/workflows/fugle-2026-entitlement-probe.yml",
        ".github/workflows/fugle-paid-api-acceptance.yml",
    )

    def test_paid_workflows_enable_atomic_claim_with_write_permission(self):
        for path in self.WORKFLOWS:
            with self.subTest(path=path):
                content = Path(path).read_text(encoding="utf-8")
                self.assertIn("SKY_PAID_ATOMIC_ENFORCE: \"1\"", content)
                self.assertIn("GH_TOKEN: ${{ github.token }}", content)
                self.assertIn("contents: write", content)
                if path.endswith("fugle-paid-api-acceptance.yml"):
                    self.assertIn("guard_fugle_request(req.full_url)", content)
                    self.assertIn("actions/checkout@v4", content)


if __name__ == "__main__":
    unittest.main()
