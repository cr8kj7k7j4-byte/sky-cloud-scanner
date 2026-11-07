import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "research" / "finmind_to_google_sheets.py"
spec = importlib.util.spec_from_file_location("finmind_to_google_sheets", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def valid():
    return {"overall":"PASS", "research_only":True, "symbol":"6770",
            "datasets":{
               "price":{"latest_rows":[{"date":"2026-11-06","stock_id":"6770",
                         "open":49.35,"max":54.3,"min":49.35,"close":52.9,
                         "Trading_Volume":149714585}]},
               "margin":{"latest_rows":[{"date":"2026-11-06","stock_id":"6770",
                         "MarginPurchaseTodayBalance":118989,
                         "ShortSaleTodayBalance":1175}]}}}

class TestBridge(unittest.TestCase):
    def test_valid(self):
        row = module.build_row(valid(), "42")
        self.assertEqual(row[0:2], ["2026-11-06", "6770"])
        self.assertEqual(row[6], 52.9)
    def test_reject_unaccepted(self):
        v=valid();v["overall"]="FAIL"
        with self.assertRaises(ValueError): module.build_row(v, "42")
    def test_reject_crossed_date(self):
        v=valid();v["datasets"]["margin"]["latest_rows"][0]["date"]="2026-11-05"
        with self.assertRaises(ValueError): module.build_row(v, "42")
    def test_reject_wrong_symbol(self):
        v=valid();v["datasets"]["price"]["latest_rows"][0]["stock_id"]="2330"
        with self.assertRaises(ValueError): module.build_row(v, "42")

if __name__ == "__main__":
    unittest.main()
