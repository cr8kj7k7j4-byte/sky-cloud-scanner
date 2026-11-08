import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from research import scan_history_fugle_markout as runner


class FugleHistoricalRunnerTests(unittest.TestCase):
    def test_missing_key_fails_closed(self):
        with patch("sys.argv", ["markout", "--end", "2026-11-06"]), patch.dict(os.environ, {"FUGLE_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "missing_FUGLE_API_KEY"):
                runner.main()

    def test_real_provider_contract_with_mocked_bars_is_research_only(self):
        from datetime import datetime, timedelta, timezone
        start = datetime(2026, 8, 1, tzinfo=timezone(timedelta(hours=8)))
        bars = [{"timestamp": (start + timedelta(days=i)).isoformat(),
                 "open": 20 + i * 0.2, "high": 20.5 + i * 0.2,
                 "low": 19.5 + i * 0.2, "close": 20.1 + i * 0.2,
                 "volume": 100 + i} for i in range(65)]
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.argv", ["markout", "--symbols", "1101", "--end", "2026-11-06"]), \
                 patch.dict(os.environ, {"FUGLE_API_KEY": "test-only-not-a-real-key"}), \
                 patch.object(runner, "read_fugle", return_value=bars), \
                 patch("pathlib.Path.mkdir"), \
                 patch("pathlib.Path.write_text") as write:
                code = runner.main()
                self.assertIn(code, (0, 2))
                self.assertTrue(write.called)
                report = json.loads(write.call_args.args[0])
                self.assertTrue(report["historical_only"])
                self.assertFalse(report["production_signal"])
                self.assertEqual(len(report["results"]), 3)


if __name__ == "__main__":
    unittest.main()
