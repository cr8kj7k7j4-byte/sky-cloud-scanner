"""Price-only legacy shortcut: no ratio, capital or volume requirements."""
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.sky_margin_runtime import evaluate_margin_bundle, main
from tests.test_sky_margin_source_join import feed


def bundle():
    x = feed()
    return {
        "official_universe": x["official_universe"],
        "universe_total": x["universe_total"],
        "official_universe_source": x["official_universe_source"],
        "fugle_quotes_by_symbol": x["fugle_quotes_by_symbol"],
        "observed_at": x["observed_at"].isoformat(),
    }


class MarginRuntimeTests(unittest.TestCase):
    def test_price_only_observation_without_retired_fields_never_buys(self):
        got = evaluate_margin_bundle(bundle())
        self.assertEqual(got["screened_count"], 1)
        self.assertEqual(got["mode"], "PRICE_ONLY_OBSERVATION")
        self.assertEqual(len(got["retired_requirements"]), 3)
        self.assertNotIn("margin_ratio_pct", got["candidates"][0])
        self.assertEqual(got["trade_status"], "NO_TRADE")
        self.assertFalse(got["buy_eligible"])
        self.assertTrue(got["liquidity_unverified"])

    def test_incomplete_full_market_never_yields_top_ten(self):
        x = bundle(); x["universe_total"] = 1988
        got = evaluate_margin_bundle(x)
        self.assertEqual(got["status"], "HOLD_INCOMPLETE_UNIVERSE")
        self.assertEqual(got["candidates"], [])

    def test_removed_fields_are_not_required_or_accepted(self):
        x = bundle()
        for k in ("ratio_by_symbol", "capital_by_symbol", "volume_by_symbol"):
            x[k] = {}
            with self.assertRaisesRegex(ValueError, "RETIRED_OR_UNRECOGNIZED_SCREEN_INPUT"):
                evaluate_margin_bundle(x)
            del x[k]
        self.assertEqual(evaluate_margin_bundle(x)["screened_count"], 1)

    def test_absent_a2_does_not_use_snapshot(self):
        x = bundle(); x["fugle_quotes_by_symbol"] = {}
        got = evaluate_margin_bundle(x)
        self.assertEqual(got["screened_count"], 0)
        self.assertEqual(got["rejected_count"], 1)

    def test_price_above_limit_is_rejected(self):
        x = bundle()
        x["fugle_quotes_by_symbol"]["6217"]["lastTrade"]["price"] = 105
        got = evaluate_margin_bundle(x)
        self.assertEqual(got["screened_count"], 0)
        self.assertEqual(got["rejections"][0]["reason"], "PRICE_NOT_BELOW_100")

    def test_tpe_timezone_normalization_and_naive_rejected(self):
        x = bundle();x["observed_at"] = "2026-11-27T01:35:00+00:00"
        self.assertEqual(evaluate_margin_bundle(x)["observation_date"], "2026-11-27")
        x["observed_at"] = "2026-11-27T09:35:00"
        with self.assertRaisesRegex(ValueError, "OBSERVATION_TIMEZONE_REQUIRED"):
            evaluate_margin_bundle(x)

    def test_duplicate_and_extra_symbol_rejected(self):
        x = bundle(); x["universe_total"] = 2
        x["official_universe"].append({"symbol": "6217", "exchange": "TWSE"})
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OFFICIAL_SYMBOL"):
            evaluate_margin_bundle(x)
        x = bundle(); x["fugle_quotes_by_symbol"]["2330"] = {}
        with self.assertRaisesRegex(ValueError, "EXTRA_A2_SYMBOLS"):
            evaluate_margin_bundle(x)

    def test_cli_invalid_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            path.write_text("{}", encoding="utf-8")
            capture = StringIO()
            with redirect_stdout(capture):
                code = main(["--input-json", str(path)])
            got = json.loads(capture.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(got["trade_status"], "NO_TRADE")
            self.assertFalse(got["new_entry_authorized"])


if __name__ == "__main__":
    unittest.main()
