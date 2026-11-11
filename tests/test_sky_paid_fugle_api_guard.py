import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from research.sky_paid_fugle_api_guard import (
    artifact_name, check_reservation, prepare, slots,
)


class FugleGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 5, 10, 20, tzinfo=timezone.utc)

    def test_empty_reservations_permit_only_preflight(self):
        allowed, reason = check_reservation("fugle-global", self.now, lambda name: [])
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLEAR")

    def test_same_window_claim_blocks(self):
        name = artifact_name("fugle-global", slots(self.now)[0])
        def lookup(key):
            return [{"created_at": self.now.isoformat()}] if key == name else []
        self.assertEqual(check_reservation("fugle-global", self.now, lookup),
                         (False, "RECENT_RESERVATION"))

    def test_previous_window_recent_claim_blocks(self):
        name = artifact_name("fugle-global", slots(self.now)[1])
        def lookup(key):
            return [{"created_at": (self.now - timedelta(seconds=25)).isoformat()}] if key == name else []
        self.assertFalse(check_reservation("fugle-global", self.now, lookup)[0])

    def test_old_previous_window_expired(self):
        old = (self.now - timedelta(seconds=310)).isoformat()
        self.assertTrue(check_reservation("fugle-global", self.now,
                        lambda name: [{"created_at": old}])[0])

    def test_different_scope_different_name(self):
        self.assertNotEqual(artifact_name("a", 3), artifact_name("b", 3))

    def test_api_failure_never_returns_approval(self):
        def fail(name):
            raise RuntimeError("API_UNAVAILABLE")
        with self.assertRaisesRegex(RuntimeError, "API_UNAVAILABLE"):
            check_reservation("fugle-global", self.now, fail)

    def test_malformed_response_rejected(self):
        for response in (None, {}, [None], [{"created_at": "invalid"}]):
            with self.subTest(response=response):
                with self.assertRaises((RuntimeError, ValueError)):
                    check_reservation("fugle-global", self.now, lambda name: response)

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "NAIVE_TIMESTAMP"):
            slots(datetime(2026, 11, 11))

    def test_receipt_without_secrets_or_market_data(self):
        with TemporaryDirectory() as td:
            allowed, name, receipt = prepare("fugle-global", self.now, lambda name: [],
                                              "111", Path(td))
            self.assertTrue(allowed)
            self.assertEqual(name, artifact_name("fugle-global", slots(self.now)[0]))
            self.assertFalse(receipt["production_eligible"])
            self.assertFalse(receipt["automatic_order"])
            self.assertIn("CLAIM_REQUIRED", receipt["status"])
            self.assertTrue((Path(td) / "claim.json").exists())


if __name__ == "__main__":
    unittest.main()
