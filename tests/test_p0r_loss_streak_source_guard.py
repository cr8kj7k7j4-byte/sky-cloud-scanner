"""P0-R: missing loss-streak evidence must never become a synthetic zero."""
import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class LossStreakSourceGuardTests(unittest.TestCase):
    def test_config_missing_history_is_unknown(self):
        with patch.dict(os.environ, {"CONSECUTIVE_LOSSES": ""}):
            cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
        self.assertIsNone(cfg["CONSECUTIVE_LOSSES"])

    def test_config_explicit_history_remains_numeric(self):
        for raw, expected in (("0", 0), ("1", 1), ("2", 2)):
            with self.subTest(raw=raw):
                with patch.dict(os.environ, {"CONSECUTIVE_LOSSES": raw}):
                    cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
                self.assertEqual(cfg["CONSECUTIVE_LOSSES"], expected)

    def test_schedule_cannot_silently_default_missing_history_to_zero(self):
        workflow = (ROOT / ".github" / "workflows" / "scan.yml").read_text(encoding="utf-8")
        self.assertIn("CONSECUTIVE_LOSSES: ${{ vars.CONSECUTIVE_LOSSES || '' }}", workflow)
        self.assertNotIn("CONSECUTIVE_LOSSES: ${{ vars.CONSECUTIVE_LOSSES || '0' }}", workflow)


if __name__ == "__main__":
    unittest.main()
