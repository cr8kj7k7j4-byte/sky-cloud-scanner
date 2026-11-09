import unittest
from datetime import datetime, timezone
from src.sky_mcp_contract import COLUMNS_13, validate_scan_result


def sample():
    row = {col: None for col in COLUMNS_13}
    row["現在動作"] = "觀察"
    return {
        "scan_id": "fresh-001",
        "source": "FUGLE",
        "data_timestamp": datetime.now(timezone.utc).isoformat(),
        "automatic_order": False,
        "rows": [row],
        "universe_count": 2000,
        "verified_quote_count": 100,
        "coverage_pct": 5.0,
        "production_eligible": False,
        "block_reason": "DATA_BLOCKED",
        "run_url": "",
    }


class TestSkyMcpContract(unittest.TestCase):
    def test_valid_observation_even_if_blocked(self):
        p = sample()
        self.assertIs(validate_scan_result(p, expected_scan_id="fresh-001"), p)

    def test_reject_old_scan(self):
        with self.assertRaisesRegex(ValueError, "SCAN_ID_MISMATCH"):
            validate_scan_result(sample(), expected_scan_id="fresh-002")

    def test_reject_non_fugle(self):
        p = sample()
        p["source"] = "MIS"
        with self.assertRaisesRegex(ValueError, "NON_FUGLE"):
            validate_scan_result(p, expected_scan_id="fresh-001")

    def test_reject_missing_column(self):
        p = sample()
        del p["rows"][0]["停損／失效"]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_13_COLUMN"):
            validate_scan_result(p, expected_scan_id="fresh-001")

    def test_reject_entry_while_blocked(self):
        p = sample()
        p["rows"][0]["現在動作"] = "買進"
        with self.assertRaisesRegex(ValueError, "BLOCKED_REPORT"):
            validate_scan_result(p, expected_scan_id="fresh-001")

    def test_reject_no_order_assertion(self):
        p = sample()
        p["automatic_order"] = True
        with self.assertRaisesRegex(ValueError, "ORDER_PERMISSION"):
            validate_scan_result(p, expected_scan_id="fresh-001")


if __name__ == "__main__":
    unittest.main()
