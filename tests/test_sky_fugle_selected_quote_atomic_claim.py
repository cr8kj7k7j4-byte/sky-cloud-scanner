import unittest
from unittest.mock import Mock
from research.sky_fugle_selected_quote_atomic_claim import (
    claim_selected_quotes, verify_selected_receipt, verify_remote_claims, validate_symbols,
)


class SelectedQuoteAtomicClaimTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.slot = 5981400

    def test_unique_symbols_and_single_claim_each(self):
        calls = []
        def git_create(ref, sha):
            calls.append((ref, sha))
            return {"status": 201, "ref": ref}
        receipt = claim_selected_quotes(
            "2330, 6488,2330", sha=self.sha, slot=self.slot,
            create_ref=git_create)
        self.assertEqual(receipt["symbols"], ["2330", "6488"])
        self.assertEqual(len(calls), 2)
        verify_selected_receipt(receipt, raw="2330,6488",
                                sha=self.sha, slot=self.slot)

    def test_duplicate_ref_never_yields_approved_receipt(self):
        first = True
        def git_create(ref, sha):
            nonlocal first
            if first:
                first = False
                return {"status": 201, "ref": ref}
            return {"status": 422, "existing": True}
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE_SELECTED"):
            claim_selected_quotes("2330,6488", sha=self.sha,
                                  slot=self.slot, create_ref=git_create)

    def test_invalid_symbol_rejected_before_any_write(self):
        calls = []
        for value in ("2330,", "", "2330,evil", "0000", ",".join(["2330"] * 21)):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    claim_selected_quotes(value, sha=self.sha, slot=self.slot,
                                          create_ref=lambda ref, sha: calls.append(ref))
        self.assertEqual(calls, [])

    def test_readback_rejects_wrong_sha_slot_or_symbols(self):
        receipt = claim_selected_quotes("2330", sha=self.sha, slot=self.slot,
              create_ref=lambda ref, sha: {"status": 201, "ref": ref})
        for kwargs in ({"raw": "6488", "sha": self.sha, "slot": self.slot},
                       {"raw": "2330", "sha": "b"*40, "slot": self.slot},
                       {"raw": "2330", "sha": self.sha, "slot": self.slot+1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(RuntimeError):
                    verify_selected_receipt(receipt, **kwargs)

    def test_remote_ref_readback_matches_same_commit(self):
        receipt = claim_selected_quotes("2330,6488", sha=self.sha, slot=self.slot,
             create_ref=lambda ref, sha: {"status": 201, "ref": ref})
        rows = receipt["claims"]
        expected = "".join(f"{self.sha}\t{row['claim_ref']}\n" for row in rows)
        runner = Mock(return_value=Mock(stdout=expected))
        verify_remote_claims(receipt, git=runner)
        self.assertEqual(runner.call_count, 1)

    def test_missing_or_different_remote_ref_fails_closed(self):
        receipt = claim_selected_quotes("2330", sha=self.sha, slot=self.slot,
             create_ref=lambda ref, sha: {"status": 201, "ref": ref})
        for stdout in ("", f"{'b'*40}\t{receipt['claims'][0]['claim_ref']}\n"):
            with self.subTest(stdout=stdout):
                with self.assertRaisesRegex(RuntimeError, "REMOTE_ATOMIC_CLAIM_READBACK_MISMATCH"):
                    verify_remote_claims(receipt, git=lambda *args, **kwargs: Mock(stdout=stdout))

    def test_paid_job_has_no_write_permissions(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] /
                  ".github/workflows/sky-selected-quote-view.yml").read_text()
        self.assertIn("needs: atomic_quote_claim", source)
        self.assertIn("if: needs.atomic_quote_claim.result == 'success'", source)
        claim_job, paid_job = source.split("  quote:\n", 1)
        self.assertIn("contents: write", claim_job)
        self.assertIn("contents: read", paid_job)
        self.assertNotIn("contents: write", paid_job)
        self.assertIn("sky_fugle_selected_quote_atomic_claim --verify", paid_job)


if __name__ == "__main__":
    unittest.main()
