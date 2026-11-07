import unittest
from research.gcs_evidence_health import safe_health, summary_markdown
from research.disclosure_gcs_readback import REQUIRED


def receipts():
    return (
        {"state":"GCS_READBACK_VERIFIED","production_signal":False,
         "prefix":"disclosure-forward/v1/run-42425505869-attempt-1",
         "objects":{name:{"readback_verified":True,"sha256":"a"*64}
                    for name in REQUIRED}},
        {"status":"GCS_CROSSDAY_LEDGER_READBACK_PASS","production_signal":False,
         "source_batches":2,"unique_provisional_events":2271,
         "cumulative_counts":{"unchanged":2271,"revision":0,"skipped_invalid":0},
         "object_path":"disclosure-forward-ledgers/v1/run-42425505869-attempt-1/ledger.json",
         "eligible_trade_events":0,"issuer_original_published_at_verified":False,
         "retention_iam_gate":"NOT_VERIFIED"}
    )


class HealthTests(unittest.TestCase):
    def test_two_batches_not_claimed_as_trading_days(self):
        result = safe_health(*receipts())
        summary = summary_markdown(result)
        self.assertEqual(result["unique_provisional_events"],2271)
        self.assertIn("不是獨立交易日", summary)
        self.assertFalse(result["positive_expectancy_verified"])

    def test_missing_raw_receipt_rejected(self):
        raw, ledger=receipts()
        del raw["objects"][REQUIRED[0]]
        with self.assertRaisesRegex(ValueError,"FOUR_SOURCE"):
            safe_health(raw,ledger)

    def test_wrong_four_sources_rejected(self):
        raw, ledger=receipts()
        raw["objects"].pop(REQUIRED[0])
        raw["objects"]["FAKE_SOURCE"] = {"readback_verified":True,"sha256":"a"*64}
        with self.assertRaisesRegex(ValueError,"FOUR_SOURCE"):
            safe_health(raw,ledger)

    def test_no_unverified_pit_promotion(self):
        raw, ledger=receipts()
        ledger["eligible_trade_events"]=1
        with self.assertRaisesRegex(ValueError,"SAFETY_GATE"):
            safe_health(raw,ledger)

    def test_no_false_iam_attestation(self):
        raw,ledger=receipts()
        ledger["retention_iam_gate"]="PASS"
        with self.assertRaisesRegex(ValueError,"POLICY"):
            safe_health(raw,ledger)


if __name__ == "__main__":
    unittest.main()
