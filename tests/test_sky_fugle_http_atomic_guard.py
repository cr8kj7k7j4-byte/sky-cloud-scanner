import os
import unittest
from unittest.mock import patch
from src import fugle


class FugleHttpAtomicGuardTests(unittest.TestCase):
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
