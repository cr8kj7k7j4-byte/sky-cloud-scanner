"""Static regression checks: live trading entrypoints never fall back to MIS.

These are source-level guards, not a substitute for paid REST entitlement tests.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def called_functions(filename):
    root = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    return {
        node.func.id
        for node in ast.walk(root)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


class FuglePrimaryRouteTests(unittest.TestCase):
    def test_daytrade_requires_fugle_snapshot_not_mis(self):
        calls = called_functions("src/main.py")
        self.assertIn("fetch_fugle_snapshot_quotes", calls)
        self.assertNotIn("fetch_mis_quotes", calls)

    def test_swing_requires_fugle_snapshot_not_mis(self):
        calls = called_functions("src/swing_live_scanner.py")
        self.assertIn("fetch_fugle_snapshot_quotes", calls)
        self.assertNotIn("fetch_mis_quotes", calls)

    def test_swing_v11_uses_fugle_quote_not_mis(self):
        calls = called_functions("src/swing_v11_live_scanner.py")
        self.assertIn("get_quote", calls)
        self.assertNotIn("fetch_mis_quotes", calls)


if __name__ == "__main__":
    unittest.main()
