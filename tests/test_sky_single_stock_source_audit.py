"""Offline, no provider calls: bounded 5m/trades evidence never grants trading."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.sky_single_stock_source_audit import analyze, collect, render_mobile_source_audit, MAX_TRADES_PAGES

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 27, 12, 7, tzinfo=TPE)


def epoch(t):
    return int(t.timestamp() * 1_000_000)


def fixture():
    q = {
        "date": "2026-11-27", "lastTrade": {
            "price": 18.9, "time": epoch(NOW - timedelta(seconds=20))},
        "total": {"tradeVolume": 3},
    }
    bars = {"data": [
        {"date": "2026-11-27T12:00:00+08:00",
         "open": 18.8, "high": 19, "low": 18.7, "close": 18.9,
         "volume": 3, "average": 18.9},
        {"date": "2026-11-27T12:05:00+08:00",
         "open": 18.9, "high": 19, "low": 18.85, "close": 18.9,
         "volume": 1, "average": 18.9},
    ]}
    ticks = [
        {"offset": 0, "data": [
            {"time": epoch(NOW - timedelta(minutes=3)),
             "serial": 100, "price": 18.8, "size": 1},
            {"time": epoch(NOW - timedelta(minutes=2)),
             "serial": 101, "price": 19.0, "size": 2},
        ]},
        {"offset": 500, "data": []},
    ]
    return q, bars, ticks


class SourceAuditTests(unittest.TestCase):
    def test_completed_only_and_bounded_pages_research_not_production(self):
        q, bars, pages = fixture()
        result = analyze("3717", q, bars, pages, observed_at=NOW)
        self.assertEqual(result["quote_status"], "PASS_ACTUAL_LAST_TRADE_REFERENCE")
        self.assertEqual(result["five_minute_status"], "PASS_COMPLETED_BARS_OBSERVED")
        self.assertEqual(result["completed_bar_count"], 1)
        self.assertEqual(result["excluded_incomplete_bar_count"], 1)
        self.assertEqual(result["trades_status"], "PASS_PAGED_RESEARCH_ARITHMETIC_ONLY")
        self.assertEqual(result["volume_status"], "RECONCILED_SAME_SNAPSHOT_NOT_CROSS_SOURCE_CERTIFIED")
        self.assertEqual(result["vwap_status"], "RESEARCH_ONLY_NO_ATOMIC_PIT_PROOF")
        self.assertFalse(result["independent_vwap_certified"])
        self.assertFalse(result["execution_authorized"])

    def test_mobile_report_from_same_result_never_promotes_vwap(self):
        q, bars, pages = fixture()
        result = analyze("3717", q, bars, pages, observed_at=NOW)
        report = render_mobile_source_audit(result)
        self.assertIn("Sky 5m驗證 3717", report)
        self.assertIn("2026-11-27", report)
        self.assertIn("已完成 K 棒", report)
        self.assertIn("TWSE 外部成交量對帳 | HOLD", report)
        self.assertIn("正式 VWAP 認證 | HOLD", report)
        self.assertIn("禁止依此報告新進場", report)
        self.assertNotIn("| 正式 VWAP 認證 | PASS", report)
        failed = render_mobile_source_audit({"symbol": "3717", "collection_error_type": "PermissionError"})
        self.assertIn("PermissionError", failed)
        self.assertIn("待確認", failed)
        self.assertNotIn("PASS", failed)

    def test_missing_terminal_and_bad_bars_do_not_certify(self):
        q, bars, pages = fixture()
        self.assertEqual(analyze("3717", q, bars, pages[:-1], observed_at=NOW)["trades_status"], "HOLD")
        bars["data"][0]["date"] = "2026-11-27T12:02:00+08:00"
        self.assertEqual(analyze("3717", q, bars, pages, observed_at=NOW)["five_minute_status"], "HOLD")

    def test_max_pages_guard_rejects_unbounded_calls_before_network(self):
        with self.assertRaises(ValueError):
            collect("3717", max_pages=MAX_TRADES_PAGES + 1)
        with self.assertRaises(ValueError):
            collect("not-a-stock")

    def test_paid_requests_bounded_and_never_retry_after_failure(self):
        q, bars, ticks = fixture()
        pages = [dict(data=x["data"]) for x in ticks]
        with patch("src.sky_single_stock_source_audit.fugle.get_quote", return_value=q) as quote, \
             patch("src.sky_single_stock_source_audit.fugle.get_candles", return_value=bars) as candles, \
             patch("src.sky_single_stock_source_audit.fugle.get_trades", side_effect=pages) as trades:
            result = collect("3717")
        quote.assert_called_once()
        candles.assert_called_once_with("3717", timeframe="5")
        self.assertEqual(trades.call_count, 2)
        self.assertNotEqual(result["five_minute_status"], "HOLD_PROVIDER_OR_TRANSPORT")
        with patch("src.sky_single_stock_source_audit.fugle.get_quote", side_effect=PermissionError("deny")) as quote:
            result = collect("3717")
        quote.assert_called_once()
        self.assertEqual(result["collection_error_type"], "PermissionError")
        self.assertNotIn("deny", str(result))
        self.assertFalse(result["production_eligible"])

    def test_existing_workflow_opt_in_only_and_owner(self):
        from pathlib import Path
        s = Path(".github/workflows/sky-single-stock-realtime.yml").read_text(encoding="utf-8")
        self.assertIn("SKY_FUGLE_MONTHLY_RATE_CONTROL: \"1\"", s)
        self.assertNotIn("SKY_PAID_ATOMIC_ENFORCE: \"1\"", s)
        self.assertIn("github.event.comment.author_association == 'OWNER'", s)
        self.assertIn('out.write(f"audit=', s)
        self.assertIn("steps.request.outputs.audit == 'true'", s)
        self.assertIn("steps.request.outputs.audit != 'true'", s)
        self.assertNotIn("\\n  schedule:", s)


if __name__ == "__main__":
    unittest.main()
