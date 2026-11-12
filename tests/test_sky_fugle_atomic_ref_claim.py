import unittest
from research.sky_fugle_atomic_ref_claim import claim_ref, try_claim
from research.sky_fugle_request_identity import canonical_fugle_request


class AtomicClaimContractTests(unittest.TestCase):
    def setUp(self):
        self.scope = canonical_fugle_request("GET", "/intraday/quote/2330")
        self.ref = claim_ref(self.scope, 5981278)
        self.sha = "a" * 40

    def test_same_endpoint_from_distinct_runs_same_claim_ref(self):
        other = canonical_fugle_request("GET", "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/2330")
        self.assertEqual(self.ref, claim_ref(other, 5981278))
        self.assertNotEqual(self.ref, claim_ref(other, 5981279))

    def test_two_independent_workflows_have_exactly_one_atomic_winner(self):
        existing = set()
        def fake_github_atomic_create(ref, sha):
            if ref in existing:
                return {"status": 422, "existing": True}
            existing.add(ref)
            return {"status": 201, "ref": ref}
        self.assertTrue(try_claim(self.ref, self.sha, fake_github_atomic_create))
        self.assertFalse(try_claim(self.ref, "b" * 40, fake_github_atomic_create))
        self.assertEqual(len(existing), 1)

    def test_uncertain_race_result_must_fail_closed(self):
        for response in (None, {}, {"status": 201}, {"status": 422}, {"status": 403}):
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError):
                    try_claim(self.ref, self.sha, lambda ref, sha: response)

    def test_transport_failure_never_authorizes_paid_request(self):
        def offline(ref, sha):
            raise RuntimeError("GITHUB_UNAVAILABLE")
        with self.assertRaisesRegex(RuntimeError, "GITHUB_UNAVAILABLE"):
            try_claim(self.ref, self.sha, offline)

    def test_reject_noncanonical_scope(self):
        with self.assertRaises(ValueError):
            claim_ref("sky:paid:workflow:abc", 5981278)


if __name__ == "__main__":
    unittest.main()
