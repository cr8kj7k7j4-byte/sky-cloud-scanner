"""Offline tests: never import Nova SDK or access account credentials."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("nova_probe", Path(__file__).resolve().parents[1] / "tools" / "nova_quote_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class TestQuoteNormalization(unittest.TestCase):
    def test_valid(self):
        d = probe.normalize("2330", {"symbol":"2330","date":"2026-11-06","closePrice":2135,
            "closeTime":"2026-11-06T13:30:00+08:00","market":"TSE",
            "total":{"tradeVolume":96950}}, "2026-11-07T01:00:00+00:00")
        self.assertTrue(d["valid_basic_quote"])
        self.assertEqual(d["trade_volume_raw"], 96950)

    def test_wrong_symbol(self):
        d = probe.normalize("2330", {"symbol":"8088","date":"2026-11-06","closePrice":35.7},
                            "2026-11-07T01:00:00+00:00")
        self.assertFalse(d["valid_basic_quote"])

    def test_missing_price(self):
        d = probe.normalize("8088", {"symbol":"8088","date":"2026-11-06"}, "2026-11-07T01:00:00+00:00")
        self.assertFalse(d["valid_basic_quote"])

    def test_unsupported(self):
        with self.assertRaises(TypeError):
            probe.normalize("2330", object(), "2026-11-07T01:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
