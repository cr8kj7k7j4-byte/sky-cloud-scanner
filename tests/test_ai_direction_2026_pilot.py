"""No credential or historical source => cannot produce a success claim."""
import unittest
from datetime import date

from research.ai_direction_2026_pilot import run


class PilotSafetyTests(unittest.TestCase):
    def test_missing_key_rejected_before_calls(self):
        calls=[]
        def reader(*args):
            calls.append(args)
            return []
        with self.assertRaisesRegex(ValueError, "FUGLE_API_KEY"):
            run(api_key="", start=date(2026,1,1), end=date(2026,11,7), reader=reader)
        self.assertEqual(calls, [])

    def test_future_window_rejected(self):
        with self.assertRaisesRegex(ValueError, "unavailable_date_window"):
            run(api_key="FAKE", start=date(2026,1,1), end=date(2027,11,7),
                reader=lambda *args: [])

    def test_duplicate_symbols_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_symbol_list"):
            run(api_key="FAKE", start=date(2026,1,1), end=date(2026,11,7),
                symbols=("1101", "1101"), reader=lambda *args: [])


if __name__ == "__main__":
    unittest.main()
