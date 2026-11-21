import os
import unittest
from unittest.mock import patch
from src import fugle


# Every test starts with an empty in-process response cache.


class FugleHttpAtomicGuardTests(unittest.TestCase):
    def setUp(self):
        fugle._ATOMIC_CACHE.clear()

    def tearDown(self):
        fugle._ATOMIC_CACHE.clear()

    def test_same_process_reuses_verified_response_without_second_paid_http(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("src.fugle._headers", return_value={"X-API-KEY": "TEST"}), \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request") as guard, \
             patch("src.fugle.requests.get") as http:
            http.return_value.json.return_value = {"data": [1]}
            first = fugle.get_quote("2330")
            first["data"].append(99)
            self.assertEqual(fugle.get_quote("2330"), {"data": [1]})
            guard.assert_called_once()
            http.assert_called_once()

    def test_cache_expires_at_atomic_slot_boundary(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("src.fugle._headers", return_value={"X-API-KEY": "TEST"}), \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request") as guard, \
             patch("src.fugle.requests.get") as http, \
             patch("src.fugle.time.time", side_effect=[299.0, 301.0]):
            http.return_value.json.return_value = {"status": "MOCK_ONLY"}
            fugle.get_quote("2330")
            fugle.get_quote("2330")
            self.assertEqual(guard.call_count, 2)
            self.assertEqual(http.call_count, 2)

    def test_distinct_endpoints_require_distinct_claims(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("src.fugle._headers", return_value={"X-API-KEY": "TEST"}), \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request") as guard, \
             patch("src.fugle.requests.get") as http:
            http.return_value.json.return_value = {"status": "MOCK_ONLY"}
            fugle.get_quote("2330")
            fugle.get_quote("2317")
            self.assertEqual(guard.call_count, 2)
            self.assertEqual(http.call_count, 2)

    def test_enforced_claim_denial_never_calls_provider(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("src.fugle._headers", return_value={"X-API-KEY": "TEST"}), \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request", side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")) as guard, \
             patch("src.fugle.requests.get") as http:
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"):
                fugle.get_quote("2330")
            guard.assert_called_once()
            http.assert_not_called()

    def test_allowed_claim_precedes_exactly_one_http_call(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("src.fugle._headers", return_value={"X-API-KEY": "TEST"}), \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request") as guard, \
             patch("src.fugle.requests.get") as http:
            http.return_value.json.return_value = {"status": "MOCK_ONLY"}
            self.assertEqual(fugle.get_quote("2330"), {"status": "MOCK_ONLY"})
            guard.assert_called_once()
            http.assert_called_once()


if __name__ == "__main__":
    unittest.main()
