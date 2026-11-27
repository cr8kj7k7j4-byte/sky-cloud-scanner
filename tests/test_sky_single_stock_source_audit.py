"""Offline, no provider calls: bounded 5m/trades evidence never grants trading."""
import unittest
import json
import sys
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src.sky_single_stock_source_audit import (analyze, collect, render_mobile_source_audit,
    analyze_observation_score, render_unified_stock_research, main as source_audit_main, MAX_TRADES_PAGES)

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

    def test_usable_descriptive_metrics_never_imply_certified_entry(self):
        q, bars, pages = fixture()
        result = analyze("3717", q, bars, pages, observed_at=NOW)
        report = render_mobile_source_audit(result)
        self.assertIn("研究數據：可供觀察", report)
        self.assertIn("逐筆成交加權均價（研究級）", report)
        self.assertIn("最後成交價相對研究均價", report)
        self.assertIn("交易訊號：未認證", report)
        self.assertIn("正式 VWAP 認證 | HOLD", report)
        self.assertIn("最近已完成 5m 收盤變動 | 待確認", report)
        result["completed_bar_count"] = 2
        report2 = render_mobile_source_audit(result)
        self.assertIn("最近已完成 5m 收盤變動 | 持平 +0.00%", report2)
        missing = {"symbol": "3717", "five_minute_status": "HOLD",
                   "trades_status": "HOLD", "volume_status": "HOLD"}
        report3 = render_mobile_source_audit(missing)
        self.assertIn("研究數據：資料不足，待確認", report3)
        self.assertIn("最後成交價相對研究均價 | 待確認", report3)

    def test_unified_cli_json_artifact_is_strictly_parseable_with_newline(self):
        # Real Run 45945886272 emitted literal \\n bytes after JSON; no CI
        # may claim Artifact PASS without independent json.loads(read_text).
        q, bars, pages = fixture()
        q.update({"openPrice": 18.75, "highPrice": 19.05, "lowPrice": 18.65,
                  "changePercent": 0.8})
        result = analyze("3717", q, bars, pages, observed_at=NOW)
        result["quote_raw"] = q
        with tempfile.TemporaryDirectory() as directory:
            args = ["sky_single_stock_source_audit", "--symbol", "3717",
                    "--out-dir", directory, "--unified"]
            with patch("sys.argv", args), patch(
                "src.sky_single_stock_source_audit.collect", return_value=result
            ), redirect_stdout(StringIO()):
                source_audit_main()
            content = (Path(directory) / "3717.json").read_text(encoding="utf-8")
            decoded = json.loads(content)
            self.assertEqual(decoded["schema"], "SKY_UNIFIED_SINGLE_STOCK_RESEARCH_V1")
            self.assertEqual(decoded["symbol"], "3717")
            self.assertFalse(decoded["execution_authorized"])
            self.assertTrue(content.endswith("\n"))
            self.assertFalse(content.endswith(r"\n"))
            self.assertTrue((Path(directory) / "3717.md").is_file())
            self.assertTrue((Path(directory) / "3717-5m-source.json").is_file())
            self.assertTrue((Path(directory) / "3717-5m-source.md").is_file())

    def test_unified_owner_analysis_one_same_run_no_trade_promotion(self):
        q, bars, pages = fixture()
        q.update({"openPrice": 18.75, "highPrice": 19.05, "lowPrice": 18.65,
                  "changePercent": 0.8})
        result = analyze("3717", q, bars, pages, observed_at=NOW)
        result["quote_raw"] = q
        observed = analyze_observation_score(result)
        self.assertEqual(observed["score_status"], "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE")
        self.assertIsInstance(observed["scores"]["bull"], int)
        self.assertFalse(observed["execution_authorized"])
        report = render_unified_stock_research(result, observed)
        self.assertIn("# Sky 分析 3717", report)
        self.assertIn("多方研究評分", report)
        self.assertIn("已完成 K 棒", report)
        self.assertIn("逐筆成交加權均價", report)
        self.assertIn("正式 VWAP 認證 | HOLD", report)
        self.assertIn("未執行交易策略", report)
        self.assertNotIn("# Sky 5m驗證", report)
        self.assertNotIn("Sky 分析 3717\\nSky 分析", report)

    def test_unified_stale_or_missing_provenance_never_scores(self):
        q, bars, pages = fixture()
        q.update({"openPrice": 18.75, "highPrice": 19.05, "lowPrice": 18.65,
                  "changePercent": 0.8})
        out = analyze("3717", q, bars, pages, observed_at=NOW)
        out["quote_raw"] = q
        out["last_trade_tpe"] = (NOW - timedelta(minutes=4)).isoformat()
        out["last_trade_price"] = 18.90
        score = analyze_observation_score(out)
        self.assertIsNone(score["scores"])
        self.assertIn("待確認", render_unified_stock_research(out, score))
        out["last_trade_tpe"] = (NOW + timedelta(minutes=1)).isoformat()
        self.assertIsNone(analyze_observation_score(out)["scores"])
        out["quote_raw"] = None
        self.assertIsNone(analyze_observation_score(out)["scores"])

    def test_owner_sky_analysis_routes_to_bounded_source_not_quote_duplication(self):
        from pathlib import Path
        yaml = Path(".github/workflows/sky-single-stock-realtime.yml").read_text(encoding="utf-8")
        self.assertIn('audit = body.startswith("Sky 5m驗證 ") or body.startswith("Sky 分析 ")', yaml)
        self.assertIn('out.write(f"unified=', yaml)
        self.assertIn('src.sky_single_stock_source_audit --symbol "$SYMBOL" --unified', yaml)
        # GitHub workflow parser must see a true YAML block scalar, not a
        # literal backslash-n string (the defect after PR #779).
        self.assertIn('        run: |\n          if [', yaml)
        self.assertNotIn(r'run: |\n          if [', yaml)
        self.assertIn('            python -m src.sky_single_stock_source_audit', yaml)

        self.assertIn("steps.request.outputs.audit != 'true'", yaml)
        self.assertIn("steps.request.outputs.audit == 'true'", yaml)
        self.assertIn("sky-fugle-paid-global-research-v1-live-wholemarket", yaml)
        self.assertNotIn("\\n  schedule:", yaml)

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
