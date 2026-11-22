"""Offline regression checks for the existing historical Fugle paid request path.

No network transport, no live credentials, no orders and no strategy signals.
"""
import os
import unittest
from datetime import date
from unittest.mock import patch

from research.download_expanded import _request_chunk


class HistoryPaidAtomicGateTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 11, 16)

    def test_missing_atomic_enforcement_blocks_before_claim_or_http(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": ""}), \
             patch("research.download_expanded.guard_fugle_request") as claim:
            def no_network(*args, **kwargs):
                raise AssertionError("NETWORK_REQUESTED_WITHOUT_GUARD")
            with self.assertRaisesRegex(RuntimeError, "HISTORICAL_PAID_GUARD_REQUIRED"):
                _request_chunk("2330", self.day, self.day, request_get=no_network)
            claim.assert_not_called()

    def test_rejected_atomic_claim_prevents_http(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("research.download_expanded.guard_fugle_request",
                   side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
            def no_network(*args, **kwargs):
                raise AssertionError("HTTP_SENT_AFTER_DUPLICATE_CLAIM")
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID"):
                _request_chunk("2330", self.day, self.day, request_get=no_network)

    def test_http_429_does_not_retry_paid_request(self):
        class RateLimited:
            status_code = 429
            headers = {}
        count = []
        def rate_limited(*args, **kwargs):
            count.append(1)
            return RateLimited()
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("research.download_expanded.guard_fugle_request") as claim, \
             patch("research.download_expanded.headers", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "NO_RETRY_UNDER_ATOMIC_CLAIM"):
                _request_chunk("2330", self.day, self.day, request_get=rate_limited,
                               sleep_fn=lambda _: None)
            claim.assert_called_once()
        self.assertEqual(len(count), 1)


if __name__ == "__main__":
    unittest.main()
