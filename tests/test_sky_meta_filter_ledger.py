import json
import tempfile
import unittest
from pathlib import Path

from research.sky_meta_filter_ledger import archive_once
from tests.test_sky_meta_filter_v0_1 import observation


class ArchiveSafetyTests(unittest.TestCase):
    def test_replay_is_idempotent_and_immutably_rejects_changes(self):
        with tempfile.TemporaryDirectory() as d:
            first=observation(0,decision="REJECT",exit_proxy=None)
            item1=archive_once(first,root=Path(d))
            self.assertEqual(item1["status"],"CREATED")
            item2=archive_once(first,root=Path(d))
            self.assertEqual(item2["status"],"ALREADY_EXISTS_IDENTICAL")
            self.assertEqual(item1["object_sha256"],item2["object_sha256"])
            self.assertFalse(item1["production_eligible"])
            changed=first.copy()
            changed["model_score"]=.21
            with self.assertRaisesRegex(ValueError,"immutable_signal_conflict"):
                archive_once(changed,root=Path(d))

    def test_reject_directory_traversal_and_relative_path(self):
        with tempfile.TemporaryDirectory() as d:
            o=observation()
            o["signal_id"]="../escape"
            with self.assertRaisesRegex(ValueError,"unsafe_signal_id"):
                archive_once(o,root=Path(d))
            with self.assertRaisesRegex(ValueError,"must_be_absolute"):
                archive_once(observation(),root="relative/location")

    def test_no_hidden_production_eligibility(self):
        with tempfile.TemporaryDirectory() as d:
            o=observation()
            o["order_authorized"]=True
            with self.assertRaisesRegex(ValueError,"production_or_order_claim"):
                archive_once(o,root=Path(d))
            self.assertEqual(list(Path(d).rglob("*.json")),[])


if __name__=="__main__":
    unittest.main()
