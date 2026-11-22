"""No implicit zero-loss evidence in the scanner's P0-R environment input.

These tests never call Fugle, place orders, or use a simulated ledger.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

from src.risk_engine import evaluate_candidate

ROOT = Path(__file__).resolve().parents[1]


def _load_loss_streak(value):
    env = os.environ.copy()
    if value is None:
        env.pop("CONSECUTIVE_LOSSES", None)
    else:
        env["CONSECUTIVE_LOSSES"] = value
    return subprocess.check_output(
        [sys.executable, "-c", "from src.config import CONSECUTIVE_LOSSES; print(repr(CONSECUTIVE_LOSSES))"],
        cwd=ROOT,
        env=env,
        text=True,
    ).strip()


class P0RMissingLossStreakEnvTests(unittest.TestCase):
    def test_absent_or_blank_env_is_unknown_not_zero(self):
        self.assertEqual(_load_loss_streak(None), "None")
        self.assertEqual(_load_loss_streak(""), "None")
        self.assertEqual(_load_loss_streak("  "), "None")

    def test_explicit_env_zero_and_two_are_preserved(self):
        self.assertEqual(_load_loss_streak("0"), "0")
        self.assertEqual(_load_loss_streak("2"), "2")

    def test_missing_loss_history_blocks_new_candidate(self):
        candidate = {"entry": 50, "stop": 49, "target": 54, "grade": "A+"}
        portfolio = {"account_equity": 500000, "consecutive_losses": None}
        result = evaluate_candidate(candidate, portfolio)
        self.assertEqual(result["status"], "RISK_INPUT_REQUIRED")
        self.assertFalse(result["portfolio_allowed"])
        self.assertEqual(result["recommended_shares"], 0)


if __name__ == "__main__":
    unittest.main()
