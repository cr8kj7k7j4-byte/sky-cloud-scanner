import unittest
from research.sky_meta_filter_w0_packet import build_packet
from research.sky_meta_filter_source_gate import STRATEGY, REQUIRED


def make_registry(status="UNRESOLVED"):
    return {"strategy_id":STRATEGY, "rules":[{"rule":r,"status":status} for r in REQUIRED]}


WORKFLOW = """name: Sky Cloud Scanner v0.5 + P0-R
on:
  schedule:
    - cron: "5,15,30,50 1 * * 1-5"
jobs:
  scan:
    env:
      FUGLE_API_KEY: ${{ secrets.FUGLE_API_KEY }}
    steps:
      - run: echo PASS_FULL_MARKET_LIVE
"""


class W0PacketTests(unittest.TestCase):
    def test_packet_stays_blocked_with_current_missing_providers(self):
        item=build_packet(registry=make_registry(),workflow_text=WORKFLOW,
                          workflow_sha="a"*64,registry_sha="b"*64)
        self.assertEqual(item["historical_unresolved_provider_count"],10)
        self.assertEqual(item["admitted_candidates"],0)
        self.assertIsNone(item["approval_packet"])
        self.assertFalse(item["private_ledger_connected"])
        self.assertFalse(item["order_authorized"])
        self.assertIn("BLOCKED",item["release_status"])
        self.assertEqual(len(item["provider_matrix"]),10)

    def test_fake_resolved_rule_registry_cannot_self_certify(self):
        item=build_packet(registry=make_registry("HISTORICAL_SNAPSHOT"),
                          workflow_text=WORKFLOW,workflow_sha="c"*64,registry_sha="d"*64)
        self.assertEqual(item["historical_unresolved_provider_count"],0)
        self.assertEqual(item["trusted_signer_check"],
                         "NOT_IMPLEMENTED_NO_EXTERNAL_APPROVAL_SOURCE")
        self.assertIsNone(item["approved_decision_stream_uri"])
        self.assertEqual(item["admitted_candidates"],0)

    def test_require_source_digest(self):
        with self.assertRaisesRegex(ValueError,"workflow_sha256_required"):
            build_packet(registry=make_registry(),workflow_text=WORKFLOW,
                         workflow_sha="",registry_sha="b"*64)


if __name__=="__main__":
    unittest.main()
