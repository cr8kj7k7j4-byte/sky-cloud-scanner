"""Offline-only checks: a Sponsor-only dataset never falsely passes."""
import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "research" / "finmind_api_acceptance.py"
SPEC = importlib.util.spec_from_file_location("finmind_acceptance", SOURCE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
EXPECTED = MOD.DATASETS["margin_maintenance"][1]


class Response:
    status = 200
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, *_):
        return json.dumps(self.data).encode()


class EntitlementTests(unittest.TestCase):
    def check(self, data):
        with patch.object(MOD.urllib.request, "urlopen", return_value=Response(data)):
            _, result = MOD.probe("margin_maintenance", "TaiwanStockMarginMaintenance",
                                  EXPECTED, "TEST_SECRET", "2026-10-26", "2026-10-30")
        self.assertNotIn("TEST_SECRET", json.dumps(result))
        return result

    def test_valid_estimated_data(self):
        row = {"date": "2026-10-26", "stock_id": "2330", "margin_balance": 30,
               "margin_cost": 100.0, "margin_ratio": 0.6, "margin_maintenance": 166.7}
        result = self.check({"status": 200, "data": [row]})
        self.assertEqual(result["status"], "PASS")

    def test_empty_not_authorized(self):
        result = self.check({"status": 200, "data": []})
        self.assertEqual(result["status"], "FAIL")

    def test_api_permission_failure_in_body(self):
        result = self.check({"status": 403, "msg": "requires sponsor", "data": []})
        self.assertEqual(result["status"], "FAIL")

    def test_missing_maintenance_field(self):
        row = {"date": "2026-10-26", "stock_id": "2330", "margin_balance": 30,
               "margin_cost": 100.0, "margin_ratio": 0.6}
        result = self.check({"status": 200, "data": [row]})
        self.assertEqual(result["status"], "FAIL")

    def test_invalid_numeric_maintenance(self):
        row = {"date": "2026-10-26", "stock_id": "2330", "margin_balance": 30,
               "margin_cost": 100.0, "margin_ratio": 0.6, "margin_maintenance": None}
        result = self.check({"status": 200, "data": [row]})
        self.assertEqual(result["status"], "FAIL")

    def test_http_permission_denial(self):
        with patch.object(MOD.urllib.request, "urlopen", side_effect=HTTPError(
            "https://api.finmindtrade.com/api/v4/data", 403, "Forbidden", {}, None)):
            _, result = MOD.probe("margin_maintenance", "TaiwanStockMarginMaintenance",
                                  EXPECTED, "TEST_SECRET", "2026-10-26", "2026-10-30")
        self.assertEqual(result["http_status"], 403)
        self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
