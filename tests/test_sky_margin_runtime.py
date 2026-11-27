"""Offline SKY維持率 consumer regression; synthetic data, zero provider calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.sky_margin_runtime import evaluate_margin_bundle, main
from tests.test_sky_margin_source_join import feed


def bundle():
    data = feed()
    data["observed_at"] = data["observed_at"].isoformat()
    return data


class MarginRuntimeTests(unittest.TestCase):
    def test_synthetic_candidate_never_grants_live_or_buy(self):
        result = evaluate_margin_bundle(bundle())
        self.assertEqual(result["screened_count"], 1)
        self.assertEqual(result["execution_status"], "HOLD_LIVE_SOURCE_AND_MOBILE_E2E")
        for field in ("source_certified", "github_run_verified",
                      "artifact_independent_readback_verified", "mobile_e2e_verified",
                      "new_entry_authorized", "buy_eligible"):
            self.assertIs(result[field], False)
        self.assertEqual(result["trade_status"], "NO_TRADE")

    def test_incomplete_market_never_returns_top_ten(self):
        data = bundle()
        data["universe_total"] = 1988
        result = evaluate_margin_bundle(data)
        self.assertEqual(result["status"], "HOLD_INCOMPLETE_UNIVERSE")
        self.assertEqual(result["candidates"], [])

    def test_missing_ratio_does_not_become_zero(self):
        data = bundle()
        data["ratio_by_symbol"] = {}
        result = evaluate_margin_bundle(data)
        self.assertEqual(result["screened_count"], 0)
        self.assertEqual(result["missing_ratio_records"], 1)

    def test_missing_a2_does_not_substitute_snapshot(self):
        data = bundle()
        data["fugle_quotes_by_symbol"] = {}
        result = evaluate_margin_bundle(data)
        self.assertEqual(result["screened_count"], 0)
        self.assertEqual(result["missing_a2_quote_records"], 1)

    def test_session_timezone_is_normalized_to_taipei(self):
        data = bundle()
        data["observed_at"] = "2026-11-27T01:35:00+00:00"
        result = evaluate_margin_bundle(data)
        self.assertEqual(result["observation_date"], "2026-11-27")
        self.assertTrue(result["observed_at_tpe"].endswith("+08:00"))

    def test_missing_required_data_and_timezone_rejected(self):
        data = bundle()
        del data["capital_by_symbol"]
        with self.assertRaisesRegex(ValueError, "MISSING_MARGIN_INPUT"):
            evaluate_margin_bundle(data)
        data = bundle()
        data["observed_at"] = "2026-11-27T09:35:00"
        with self.assertRaisesRegex(ValueError, "OBSERVATION_TIMEZONE_REQUIRED"):
            evaluate_margin_bundle(data)

    def test_unknown_fields_rejected_not_silently_used(self):
        data = bundle()
        data["certified"] = True
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED_MARGIN_INPUT"):
            evaluate_margin_bundle(data)

    def test_cli_without_valid_source_emits_safe_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text("{}", encoding="utf-8")
            from contextlib import redirect_stdout
            import io
            out = io.StringIO()
            with redirect_stdout(out):
                status = main(["--input-json", str(path)])
            self.assertEqual(status, 2)
            result = json.loads(out.getvalue())
            self.assertEqual(result["trade_status"], "NO_TRADE")
            self.assertFalse(result["new_entry_authorized"])


if __name__ == "__main__":
    unittest.main()
