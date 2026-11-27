"""SKY維持率 trigger safety: synthetic GitHub events and artifact bytes."""
import copy
import json
import unittest
from src.sky_margin_trigger_receipt import make_receipt, verify_receipt

REPO = "cr8kj7k7j4-byte/sky-cloud-scanner"
SHA = "a" * 40

def event():
    return {"repository": {"full_name": REPO},
            "issue": {"number": 363},
            "comment": {"id": 12, "body": "SKY維持率",
                        "author_association": "OWNER",
                        "user": {"login": "cr8kj7k7j4-byte"}}}

def produce(e=None):
    return make_receipt(e if e is not None else event(), repo=REPO,
                        run_id="1234", attempt="1", sha=SHA)


class MarginTriggerReceiptTests(unittest.TestCase):
    def test_exact_authorized_command_only_produces_hold(self):
        r = produce()
        self.assertFalse(r["market_scan_executed"])
        self.assertTrue(r["price_only_mode"])
        self.assertTrue(r["margin_ratio_screen_retired"])
        self.assertTrue(r["capital_and_prior_volume_screen_retired"])
        self.assertIsNone(r["candidate_count"])
        self.assertFalse(r["new_entry_authorized"])
        self.assertEqual(r["trade_action"], "禁止交易")

    def test_alias_or_spacing_is_not_accepted(self):
        for cmd in ("Sky 維持率", "SKY維持率 ", "Sky 快掃", ""):
            e = event()
            e["comment"]["body"] = cmd
            with self.subTest(cmd=cmd), self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):
                produce(e)

    def test_nonowner_or_wrong_issue_denied(self):
        for field, value in (("author_association", "MEMBER"), ("user", {"login": "other"})):
            e = event(); e["comment"][field] = value
            with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):
                produce(e)
        e = event(); e["issue"]["number"] = 364
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):
            produce(e)

    def test_repository_mismatch_and_invalid_identity_denied(self):
        e=event();e["repository"]["full_name"]="attacker/other"
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):
            produce(e)
        with self.assertRaisesRegex(ValueError,"INVALID_GITHUB"):
            make_receipt(event(),repo=REPO,run_id="0",attempt="1",sha=SHA)

    def test_valid_readback_is_not_real_margin_scan(self):
        raw = json.dumps(produce(),ensure_ascii=False).encode()
        receipt = verify_receipt(raw,raw,run_id="1234",attempt="1",sha=SHA,comment_id="12")
        self.assertEqual(receipt["status"], "PASS_HOLD_RECEIPT_INTEGRITY_ONLY")
        self.assertFalse(receipt["real_margin_scan_verified"])

    def test_modified_bytes_are_rejected(self):
        raw=json.dumps(produce()).encode()
        with self.assertRaisesRegex(ValueError,"BYTES_MISMATCH"):
            verify_receipt(raw,raw+b" ",run_id="1234",attempt="1",sha=SHA,comment_id="12")

    def test_mismatched_run_or_attempt_denied(self):
        raw=json.dumps(produce()).encode()
        for key,val in (("run_id","9999"),("attempt","2"),("sha","b"*40),("comment_id","99")):
            opts=dict(run_id="1234",attempt="1",sha=SHA,comment_id="12")
            opts[key]=val
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"IDENTITY"):
                verify_receipt(raw,raw,**opts)

    def test_forged_trade_eligibility_denied(self):
        for key,val in (("market_scan_executed",True),("new_entry_authorized",True),
                        ("production_eligible",True),("trade_action","買進")):
            r=produce();r[key]=val
            raw=json.dumps(r).encode()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"SAFETY"):
                verify_receipt(raw,raw,run_id="1234",attempt="1",sha=SHA,comment_id="12")

if __name__ == "__main__":
    unittest.main()
