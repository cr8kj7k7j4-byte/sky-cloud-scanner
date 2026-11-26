"""Regression tests: no live calls or fabricated market data."""
import unittest
from src.sky_margin_research_filter import filter_margin_observations


def row(symbol="6217", **kw):
    value = dict(
        symbol=symbol, exchange="TWSE",
        margin_ratio_pct="88", paid_in_capital_twd="1172000000",
        previous_volume_lots="3249", last_trade_price_twd="92.9",
        ratio_source="THIRD_PARTY_ESTIMATE", ratio_date="2026-11-26",
        ratio_method="published_estimate", capital_source="PUBLIC_FILING",
        capital_date="2026-11-26", volume_source="OFFICIAL_VOLUME",
        volume_date="2026-11-26", price_source="AUTHORIZED_QUOTE",
        price_date="2026-11-26", price_evidence="EXECUTED_TRADE",
    )
    value.update(kw)
    return value


def screen(rows, total=None):
    return filter_margin_observations(
        rows, observation_date="2026-11-27",
        previous_session_date="2026-11-26", universe_total=total or len(rows),
        universe_source="TEST_DECLARED_UNIVERSE_NOT_OFFICIAL",
    )


class MarginResearchTests(unittest.TestCase):
    def test_positive_research_only_and_source_visible(self):
        result = screen([row()])
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertEqual(result["screened_count"], 1)
        self.assertFalse(result["buy_eligible"])
        self.assertEqual(result["trade_status"], "NO_TRADE")
        self.assertEqual(result["candidates"][0]["ratio_estimate_source"], "THIRD_PARTY_ESTIMATE")

    def test_four_strict_boundaries_reject(self):
        for name, boundary in (
            ("margin_ratio_pct", "120"), ("paid_in_capital_twd", "3000000000"),
            ("previous_volume_lots", "100"), ("last_trade_price_twd", "100"),
        ):
            with self.subTest(name=name):
                self.assertEqual(screen([row(**{name: boundary})])["screened_count"], 0)

    def test_unknown_and_negative_fail_closed(self):
        for v in (None, "", "NaN", "-1", float("inf"), True):
            with self.subTest(value=v):
                res = screen([row(margin_ratio_pct=v)])
                self.assertEqual(res["screened_count"], 0)

    def test_stale_volume_wrong_ratio_date_and_nontrade_quote(self):
        for change in (
            {"volume_date": "2026-11-25"},
            {"ratio_date": "2026-11-25"},
            {"price_evidence": "SNAPSHOT_LAST_UPDATED"},
            {"price_source": ""},
        ):
            with self.subTest(change=change):
                self.assertEqual(screen([row(**change)])["screened_count"], 0)

    def test_partial_declared_universe_does_not_rank(self):
        res = screen([row()], total=1987)
        self.assertEqual(res["status"], "HOLD_INCOMPLETE_UNIVERSE")
        self.assertEqual(res["candidates"], [])
        self.assertFalse(res["coverage_complete"])

    def test_no_duplicate_or_malformed_market(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_UNIVERSE_SYMBOL"):
            screen([row(), row()])
        with self.assertRaisesRegex(ValueError, "INVALID_SYMBOL_OR_MARKET"):
            screen([row(exchange="EXTERNAL")])

    def test_sort_and_top_ten(self):
        rows = [row(symbol=str(1000+i), margin_ratio_pct=str(99-i),
                    previous_volume_lots=str(101+i)) for i in range(12)]
        res = screen(rows)
        self.assertEqual(res["screened_count"], 12)
        self.assertEqual(len(res["candidates"]), 10)
        self.assertEqual(res["candidates"][0]["symbol"], "1011")

    def test_ratio_provider_entitlement_is_not_gate(self):
        res = screen([row(ratio_source="DISCLOSED_UNCERTIFIED_ESTIMATE")])
        self.assertEqual(res["screened_count"], 1)
        self.assertFalse(res["buy_eligible"])


if __name__ == "__main__":
    unittest.main()
