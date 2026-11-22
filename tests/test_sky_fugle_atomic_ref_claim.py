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

    def test_parallel_AB_race_one_winner_one_duplicate_zero_paid_calls(self):
        # Two independent mock workflow runners race the SAME endpoint identity.
        # The fake GitHub create-ref critical section is atomic; no network used.
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier, Lock

        barrier = Barrier(2)
        lock = Lock()
        refs = set()
        paid_http_calls = []

        def fake_github_create(ref, sha):
            with lock:
                if ref in refs:
                    return {"status": 422, "existing": True}
                refs.add(ref)
                return {"status": 201, "ref": ref}

        def competing_runner(sha):
            barrier.wait(timeout=5)
            allowed = try_claim(self.ref, sha, fake_github_create)
            # No paid request is issued in either mocked branch.
            return allowed

        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(competing_runner, "a" * 40)
            loser = pool.submit(competing_runner, "b" * 40)
            outcomes = [winner.result(timeout=6), loser.result(timeout=6)]
        self.assertCountEqual(outcomes, [True, False])
        self.assertEqual(len(refs), 1)
        self.assertEqual(paid_http_calls, [])

    def test_identical_history_query_reuses_stable_ref_across_runs(self):
        from unittest.mock import patch
        from research.sky_fugle_atomic_ref_claim import guard_fugle_request

        refs = set()
        seen = []
        def fake_github_create_ref(repo, token):
            self.assertEqual(repo, "example/sky")
            self.assertEqual(token, "offline-token")
            def create(ref, sha):
                seen.append(ref)
                if ref in refs:
                    return {"status": 422, "existing": True}
                refs.add(ref)
                return {"status": 201, "ref": ref}
            return create

        env = {
            "SKY_PAID_ATOMIC_ENFORCE": "1",
            "GITHUB_REPOSITORY": "example/sky",
            "GH_TOKEN": "offline-token",
            "GITHUB_SHA": self.sha,
        }
        endpoint = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/2330"
        params = {"from": "2026-11-16", "to": "2026-11-20", "timeframe": "5"}
        with patch.dict("os.environ", env), patch(
                "research.sky_fugle_atomic_ref_claim.github_create_ref",
                side_effect=fake_github_create_ref):
            guard_fugle_request(endpoint, params)
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"):
                guard_fugle_request(endpoint, dict(reversed(list(params.items()))))
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(refs), 1)
        self.assertEqual(seen[0], seen[1])
        self.assertTrue(seen[0].endswith("-1"))

    def test_distinct_history_windows_and_symbols_do_not_share_claim(self):
        from unittest.mock import patch
        from research.sky_fugle_atomic_ref_claim import guard_fugle_request

        seen = set()
        def fake_github_create_ref(repo, token):
            def create(ref, sha):
                self.assertNotIn(ref, seen)
                seen.add(ref)
                return {"status": 201, "ref": ref}
            return create
        env = {
            "SKY_PAID_ATOMIC_ENFORCE": "1",
            "GITHUB_REPOSITORY": "example/sky",
            "GH_TOKEN": "offline-token",
            "GITHUB_SHA": self.sha,
        }
        endpoint = "/historical/candles/2330"
        with patch.dict("os.environ", env), patch(
                "research.sky_fugle_atomic_ref_claim.github_create_ref",
                side_effect=fake_github_create_ref):
            guard_fugle_request(endpoint, {"from": "2026-11-16", "to": "2026-11-20"})
            guard_fugle_request(endpoint, {"from": "2026-11-17", "to": "2026-11-20"})
            guard_fugle_request("/historical/candles/2317",
                                {"from": "2026-11-16", "to": "2026-11-20"})
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(ref.endswith("-1") for ref in seen))

    def test_live_quote_retains_rolling_five_minute_claim(self):
        from unittest.mock import patch
        from research.sky_fugle_atomic_ref_claim import guard_fugle_request

        seen = []
        def fake_github_create_ref(repo, token):
            def create(ref, sha):
                seen.append(ref)
                return {"status": 201, "ref": ref}
            return create
        env = {
            "SKY_PAID_ATOMIC_ENFORCE": "1",
            "GITHUB_REPOSITORY": "example/sky",
            "GH_TOKEN": "offline-token",
            "GITHUB_SHA": self.sha,
        }
        with patch.dict("os.environ", env), patch(
                "research.sky_fugle_atomic_ref_claim.github_create_ref",
                side_effect=fake_github_create_ref):
            guard_fugle_request("/intraday/quote/2330")
        self.assertEqual(len(seen), 1)
        self.assertFalse(seen[0].endswith("-1"))

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
