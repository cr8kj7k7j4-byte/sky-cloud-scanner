import os
import unittest
from unittest.mock import Mock, patch

from src import fugle


class FuglePaidHttpBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1",
            "GITHUB_REPOSITORY": "research/sky", "GITHUB_SHA": "a" * 40,
            "GH_TOKEN": "test-token"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_confirmed_atomic_claim_precedes_the_http_call(self):
        mock_transport = Mock(return_value={"status": 201})
        def create_ref(ref, sha):
            self.assertEqual(sha, "a" * 40)
            mock_transport(ref, sha)
            return {"status": 201, "ref": ref}
        with patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
             patch("src.fugle.requests.get") as http, \
             patch("research.sky_fugle_atomic_ref_claim.github_create_ref", return_value=create_ref):
            http.return_value.json.return_value = {"symbol": "2330"}
            self.assertEqual(fugle.get_quote("2330")["symbol"], "2330")
            self.assertEqual(mock_transport.call_count, 1)
            self.assertEqual(http.call_count, 1)

    def test_existing_atomic_ref_blocks_paid_http(self):
        def duplicate(ref, sha):
            return {"status": 422, "existing": True}
        with patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
             patch("src.fugle.requests.get") as http, \
             patch("research.sky_fugle_atomic_ref_claim.github_create_ref", return_value=duplicate):
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"):
                fugle.get_quote("2330")
            http.assert_not_called()

    def test_uncertain_claim_blocks_without_http(self):
        with patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
             patch("src.fugle.requests.get") as http, \
             patch("research.sky_fugle_atomic_ref_claim.github_create_ref", return_value=lambda ref, sha: {"status": 403}):
            with self.assertRaisesRegex(RuntimeError, "ATOMIC_CLAIM_UNVERIFIED"):
                fugle.get_candles("2330")
            http.assert_not_called()

    def test_invalid_explicit_guard_mode_never_sends_paid_http(self):
        for mode in ("true", "0", "", "enabled"):
            with self.subTest(mode=mode), \
                 patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": mode}), \
                 patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
                 patch("src.fugle.requests.get") as http:
                with self.assertRaisesRegex(RuntimeError, "INVALID_ATOMIC_ENFORCEMENT_MODE"):
                    fugle.get_quote("2330")
                http.assert_not_called()

    def test_opt_in_off_retains_existing_behavior(self):
        os.environ.pop("SKY_PAID_ATOMIC_ENFORCE", None)
        with patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
             patch("src.fugle.requests.get") as http:
            http.return_value.json.return_value = {"ok": True}
            self.assertEqual(fugle.get_quote("2330"), {"ok": True})
            http.assert_called_once()

    def test_invalid_request_fails_before_http(self):
        with patch("src.fugle._headers", return_value={"X-API-KEY": "test"}), \
             patch("src.fugle.requests.get") as http:
            with self.assertRaises(ValueError):
                fugle._get("/unapproved/path")
            http.assert_not_called()


if __name__ == "__main__":
    unittest.main()
