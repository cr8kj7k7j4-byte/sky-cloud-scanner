import unittest
from research.fugle_event_backtest_gate import assess


def example():
    return {"production_signal":False,"events":{"record1":{
        "provisional_identity":{"category":"MONTHLY_REVENUE"},
        "first_observed_at_utc":"2026-11-08T05:30:00+08:00",
        "issuer_original_published_at":None,
        "issuer_publication_source_verified":False,
    }}}


class EventReplayReadinessTests(unittest.TestCase):
    def test_unverified_revenue_cannot_replay(self):
        x=assess(example())
        self.assertEqual(x["revenue_event_evidence_candidates"],0)
        self.assertEqual(x["event_backtest_trades_executed"],0)
        self.assertFalse(x["production_signal"])
        self.assertEqual(x["rejections"]["MISSING_OR_UNVERIFIED_ORIGINAL_FILING"],1)

    def test_false_claimed_publication_still_rejected_without_receipt(self):
        x=example()
        row=x["events"]["record1"]
        row["issuer_original_published_at"]="2026-11-08T05:20:00+08:00"
        row["issuer_publication_source_verified"]=True
        q=assess(x)
        self.assertEqual(q["revenue_event_evidence_candidates"],0)
        self.assertEqual(q["rejections"]["UNVERIFIED_FILING_RECEIPT"],1)

    def test_bad_timestamp_order_rejected(self):
        x=example()
        row=x["events"]["record1"]
        row["issuer_original_published_at"]="2026-11-08T05:40:00+08:00"
        row["issuer_publication_source_verified"]=True
        row["independent_filing_verification_receipt_sha256"]="hashplaceholder"
        q=assess(x)
        self.assertEqual(q["revenue_event_evidence_candidates"],0)
        self.assertEqual(q["rejections"]["TIMESTAMP_ORDER_INVALID"],1)

    def test_non_revenue_event_is_not_revenue_strategy(self):
        x=example()
        x["events"]["record1"]["provisional_identity"]["category"]="MATERIAL_DISCLOSURE"
        q=assess(x)
        self.assertEqual(q["rejections"]["NOT_REVENUE_EVENT"],1)

    def test_refuse_unsafe_prior_ledger(self):
        x=example()
        x["production_signal"]=True
        with self.assertRaises(ValueError):
            assess(x)


if __name__=="__main__":
    unittest.main()
