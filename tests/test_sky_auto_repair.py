"""Bounded fail-closed Sky auto-repair unit contracts (no credentials/network)."""
import unittest
from unittest.mock import patch

from scripts.sky_auto_repair import prepare_safe_patch, run


class AutoRepairContracts(unittest.TestCase):
    def test_no_change_to_correct_contract(self):
        self.assertIsNone(prepare_safe_patch('x = {"snapshot_reference_requires_last_trade_time": False}'))

    def test_narrow_repair(self):
        text = 'x = {"snapshot_reference_requires_last_trade_time": True, "production_eligible": False}'
        result = prepare_safe_patch(text)
        self.assertIn('"snapshot_reference_requires_last_trade_time": False,', result)
        self.assertIn('"production_eligible": False', result)

    def test_duplicate_anchor_fails_closed(self):
        with self.assertRaises(RuntimeError):
            prepare_safe_patch('x={"snapshot_reference_requires_last_trade_time": True, "snapshot_reference_requires_last_trade_time": True,}')

    def test_closed_pr_does_not_write(self):
        fake_pr = {"state": "closed", "draft": True,
                   "head": {"sha": "deadbeef", "ref": "research/fugle-snapshot-diagnostics-20261110"}}
        with patch("scripts.sky_auto_repair.api", return_value=fake_pr) as fn:
            status = run()
        self.assertEqual(status["self_review"], "HOLD")
        self.assertIn("PR_NOT_OPEN_DRAFT_EXPECTED_BRANCH", status["blockers"])
        fn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
