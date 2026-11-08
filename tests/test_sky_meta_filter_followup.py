import hashlib
import tempfile
import unittest
from pathlib import Path

from research.sky_meta_filter_followup import append_followup_once
from research.sky_meta_filter_ledger import archive_once, canonical
from tests.test_sky_meta_filter_v0_1 import observation


def initial():
    return observation(0,decision="REJECT",exit_proxy=None)


def followup(item):
    return {"schema":"sky-meta-filter-followup-v0.1",
            "signal_id":item["signal_id"],
            "observation_sha256":hashlib.sha256(canonical(item)).hexdigest(),
            "exit_at":"2026-11-09T13:20:00+08:00",
            "exit_proxy":49.5,
            "counterfactual_evidence_verified":True,
            "actual_fill":False,"production_eligible":False}


class FollowupTests(unittest.TestCase):
    def test_create_once_then_identical_replay(self):
        with tempfile.TemporaryDirectory() as d:
            o=initial()
            archive_once(o,root=Path(d))
            f=followup(o)
            a=append_followup_once(o,f,root=d)
            self.assertEqual(a["status"],"CREATED")
            self.assertEqual(append_followup_once(o,f,root=d)["status"],
                             "ALREADY_EXISTS_IDENTICAL")
            self.assertTrue(a["counterfactual_only"])
            self.assertEqual(list(Path(d).rglob("followups/**/*.json"))!=[], True)

    def test_different_outcome_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            o=initial()
            archive_once(o,root=d)
            f=followup(o)
            append_followup_once(o,f,root=d)
            f["exit_proxy"]=52
            with self.assertRaisesRegex(ValueError,"immutable_followup_conflict"):
                append_followup_once(o,f,root=d)

    def test_missing_original_observation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            o=initial()
            with self.assertRaisesRegex(ValueError,"original_immutable_observation_missing"):
                append_followup_once(o,followup(o),root=d)

    def test_wrong_digest_or_future_data_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            o=initial()
            archive_once(o,root=d)
            f=followup(o)
            f["observation_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"digest_mismatch"):
                append_followup_once(o,f,root=d)
            f=followup(o)
            f["exit_at"]="2026-11-09T09:00:00+08:00"
            with self.assertRaisesRegex(ValueError,"invalid_intraday_exit_at"):
                append_followup_once(o,f,root=d)


if __name__ == "__main__":
    unittest.main()
