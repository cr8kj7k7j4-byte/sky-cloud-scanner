"""Tests for single-stock realtime freshness and failure handling."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.sky_single_stock_realtime import collect, timestamp_tpe

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 3, 10, 10, tzinfo=TPE)


def epoch_us(dt):
    return int(dt.timestamp() * 1000000)


class SingleStockRealtimeTests(unittest.TestCase):
    def test_minimal_single_stock_owner_comment_is_strictly_bound(self):
        # The existing paid quote Workflow is reused; no new runner or cron.
        import re
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / ".github/workflows/sky-single-stock-realtime.yml"
        source = path.read_text(encoding="utf-8")
        self.assertIn("github.event.issue.number == 363", source)
        self.assertIn("github.event.comment.author_association == 'OWNER'", source)
        self.assertIn("startsWith(github.event.comment.body, 'Sky 分析 ')", source)
        match = re.search(r'match = re.fullmatch\(r"([^"]+)"', source)
        self.assertIsNotNone(match)
        matcher = re.compile(match.group(1))
        for command in ("Sky 分析 2330", "Sky 當沖更新 2330", "Sky 波段更新 2330"):
            self.assertEqual(matcher.fullmatch(command).group(1), "2330")
        for command in ("Sky 分析", "Sky 分析 2330 任意", "Sky 分析 abc", "Sky 分析 2330\\nSKY_FAKE"):
            self.assertIsNone(matcher.fullmatch(command))

    def test_single_stock_monthly_provider_pacing_without_five_minute_billing_block(self):
        # This is the *same* previously deployed Fugle monthly pacing lane,
        # not unlimited API usage or a request for more paid probes.
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-single-stock-realtime.yml").read_text(
                        encoding="utf-8")
        self.assertIn('SKY_FUGLE_MONTHLY_RATE_CONTROL: "1"', workflow)
        self.assertNotIn('SKY_PAID_ATOMIC_ENFORCE: "1"', workflow)
        self.assertIn("sky-fugle-paid-global-research-v1-live-wholemarket", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("github.event.comment.author_association == 'OWNER'", workflow)
        self.assertIn("sky-single-stock-ignored-{0}", workflow)
        self.assertIn("if: steps.request.outcome == 'success'", workflow)

    def sample(self, minutes=0):
        t = NOW - timedelta(minutes=minutes)
        quote = {"date": "2026-11-03", "lastPrice": 92.2,
                 "lastTrade": {"time": epoch_us(t)}, "total": {"tradeVolume": 1000},
                 "bids": [{"price": 92.1}], "asks": [{"price": 92.2}]}
        ticker = {"canDayTrade": True}
        return quote, ticker

    def test_verified_quote_has_reproducible_observation_scores(self):
        quote, ticker = self.sample()
        quote.update({"openPrice": 33.0, "highPrice": 34.2, "lowPrice": 30.15,
                      "lastPrice": 30.25, "changePercent": -9.7})
        quote["lastTrade"]["price"] = 30.25
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("6140", NOW)
        self.assertEqual(result["scores"], {"bull": 14, "bear": 86})
        self.assertEqual(result["score_direction"], "偏空")
        self.assertEqual(result["score_status"], "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["live_order_enabled"])

    def test_scores_not_blocked_by_daytrade_eligibility_or_account(self):
        quote, ticker = self.sample()
        quote.update({"openPrice": 33.0, "highPrice": 34.2, "lowPrice": 30.15,
                      "lastPrice": 30.25, "changePercent": -9.7})
        quote["lastTrade"]["price"] = 30.25
        ticker["canDayTrade"] = False
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("6140", NOW)
        self.assertEqual(result["status"], "DAY_TRADE_NOT_ELIGIBLE")
        self.assertEqual(result["scores"], {"bull": 14, "bear": 86})
        self.assertFalse(result["execution_authorized"])

    def test_stale_and_missing_ohlc_never_get_observation_score(self):
        quote, ticker = self.sample(minutes=5)
        quote.update({"openPrice": 33.0, "highPrice": 34.2, "lowPrice": 30.15,
                      "lastPrice": 30.25, "changePercent": -9.7})
        quote["lastTrade"]["price"] = 30.25
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            stale = collect("6140", NOW)
        self.assertIsNone(stale["scores"])
        quote["lastTrade"]["time"] = epoch_us(NOW)
        quote.pop("highPrice")
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            missing = collect("6140", NOW)
        self.assertIsNone(missing["scores"])

    def test_quote_refresh_without_executed_price_never_gets_scores(self):
        quote, ticker = self.sample()
        quote.update({"openPrice": 33.0, "highPrice": 34.2, "lowPrice": 30.15,
                      "lastPrice": 30.25, "changePercent": -9.7})
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("6140", NOW)
        self.assertIsNone(result["scores"])

    def test_scored_price_cap_observation_cli_succeeds_without_trade_authorization(self):
        import tempfile
        import sys
        from pathlib import Path
        from src.sky_single_stock_realtime import main

        scored = {
            "symbol": "2330", "status": "PRICE_CAP_EXCEEDED",
            "score_status": "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE",
            "scores": {"bull": 72, "bear": 28},
            "execution_authorized": False, "live_order_enabled": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp) / "2330.json")
            with patch("src.sky_single_stock_realtime.collect", return_value=scored), patch.object(
                sys, "argv", ["single_stock", "--symbol", "2330", "--output", output]
            ):
                main()
            self.assertTrue(Path(output).exists())

    def test_stale_real_trade_is_research_reference_not_scan_failure(self):
        """Same-day real execution remains visible, never live or scored."""
        import tempfile
        import sys
        from pathlib import Path
        from src.sky_single_stock_realtime import main
        payload = {
            "symbol": "3717", "status": "STALE_QUOTE",
            "quote_date": "2026-11-27",
            "requested_at_tpe": "2026-11-27T12:44:00+08:00",
            "last_trade_tpe": "2026-11-27T12:40:00+08:00",
            "last_trade_price": 18.85, "quote_age_seconds": 240,
            "source": "Fugle MarketData API /intraday/quote",
            "score_status": "INSUFFICIENT_VERIFIED_OHLC",
            "scores": None, "execution_authorized": False,
            "live_order_enabled": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "3717.json"
            with patch("src.sky_single_stock_realtime.collect", return_value=payload), patch.object(
                sys, "argv", ["single_stock", "--symbol", "3717", "--output", str(output)]
            ):
                main()  # valid reference evidence is not a tool/process failure
            mobile = output.with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("最後實際成交觀察價：18.85", mobile)
            self.assertIn("現價 | 待確認（非新鮮成交）", mobile)
            self.assertIn("| 多方評分 | 待確認 |", mobile)
            self.assertIn("禁止新進場", mobile)

    def test_inconsistent_stale_reference_is_still_scan_failure(self):
        import tempfile
        import sys
        from pathlib import Path
        from src.sky_single_stock_realtime import main
        payload = {
            "symbol": "3717", "status": "STALE_QUOTE",
            "quote_date": "2026-11-27",
            "requested_at_tpe": "2026-11-27T12:44:00+08:00",
            "last_trade_tpe": "2026-11-27T12:40:00+08:00",
            "last_trade_price": 18.85, "quote_age_seconds": 3,
            "scores": None, "score_status": "INSUFFICIENT_VERIFIED_OHLC",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch("src.sky_single_stock_realtime.collect", return_value=payload), patch.object(
                sys, "argv", ["single_stock", "--symbol", "3717", "--output",
                             str(Path(tmp) / "3717.json")]
            ):
                with self.assertRaises(SystemExit) as exc:
                    main()
                self.assertEqual(exc.exception.code, 2)

    def test_unscored_invalid_quote_cli_still_fails(self):
        import tempfile
        import sys
        from pathlib import Path
        from src.sky_single_stock_realtime import main

        blocked = {
            "symbol": "2330", "status": "STALE_QUOTE",
            "score_status": "INSUFFICIENT_VERIFIED_OHLC",
            "scores": None, "execution_authorized": False,
            "live_order_enabled": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp) / "2330.json")
            with patch("src.sky_single_stock_realtime.collect", return_value=blocked), patch.object(
                sys, "argv", ["single_stock", "--symbol", "2330", "--output", output]
            ):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 2)

    def test_mobile_report_from_verified_observation_is_readable_and_no_trade(self):
        from src.sky_single_stock_realtime import render_mobile_observation
        payload = {
            "symbol": "2337", "source": "Fugle MarketData API /intraday/quote",
            "quote_date": "2026-11-27",
            "requested_at_tpe": "2026-11-27T12:17:00+08:00",
            "last_trade_tpe": "2026-11-27T12:16:54+08:00",
            "last_trade_price": 65.9, "quote_age_seconds": 6.0,
            "status": "REALTIME_QUOTE_VERIFIED",
            "score_status": "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE",
            "score_version": "SKY_OBSERVATIONAL_EVIDENCE_V1",
            "score_direction": "中性偏多",
            "scores": {"bull": 63, "bear": 37},
            "execution_authorized": False, "live_order_enabled": False,
        }
        md = render_mobile_observation(payload)
        self.assertIn("| 多方評分 | 63 |", md)
        self.assertIn("| 空方評分 | 37 |", md)
        self.assertIn("| 現價 | 65.90 |", md)
        self.assertIn("| 現在動作 | 等待 |", md)
        self.assertIn("🔴 禁止新進場", md)
        self.assertNotIn("買進：65", md)
        self.assertIn("\n| 多方評分 |", md)

    def test_stale_mobile_report_keeps_observation_but_hides_live_price_and_scores(self):
        from src.sky_single_stock_realtime import render_mobile_observation
        payload = {
            "symbol": "3717", "source": "Fugle MarketData API /intraday/quote",
            "quote_date": "2026-11-27",
            "requested_at_tpe": "2026-11-27T12:16:10+08:00",
            "last_trade_tpe": "2026-11-27T12:13:14+08:00",
            "last_trade_price": 18.85, "quote_age_seconds": 175.3,
            "status": "STALE_QUOTE", "score_status": "INSUFFICIENT_VERIFIED_OHLC",
            "scores": None, "execution_authorized": False,
            "live_order_enabled": False,
        }
        md = render_mobile_observation(payload)
        self.assertIn("| 現價 | 待確認（非新鮮成交） |", md)
        self.assertIn("| 多方評分 | 待確認 |", md)
        self.assertIn("最後實際成交觀察價：18.85", md)
        self.assertIn("實際最後成交時間：2026-11-27T12:13:14", md)
        self.assertNotIn("| 現價 | 18.85 |", md)

    def test_main_writes_same_run_json_and_mobile_markdown(self):
        import tempfile
        import sys
        from pathlib import Path
        from src.sky_single_stock_realtime import main
        payload = {
            "symbol": "2337", "status": "REALTIME_QUOTE_VERIFIED",
            "score_status": "RESEARCH_ONLY_VERIFIED_INTRADAY_QUOTE",
            "scores": {"bull": 63, "bear": 37},
            "score_direction": "中性偏多", "last_trade_price": 65.9,
            "last_trade_tpe": "2026-11-27T12:16:54+08:00",
            "quote_age_seconds": 6.0, "execution_authorized": False,
            "live_order_enabled": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "2337.json"
            with patch("src.sky_single_stock_realtime.collect", return_value=payload), patch.object(
                sys, "argv", ["single_stock", "--symbol", "2337", "--output", str(output)]
            ):
                main()
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".md").is_file())
            self.assertIn("| 多方評分 | 63 |", output.with_suffix(".md").read_text(encoding="utf-8"))

    def test_timestamp_conversion(self):
        self.assertEqual(timestamp_tpe(epoch_us(NOW)), NOW.isoformat())

    def test_current_quote_no_synthetic_levels(self):
        quote, ticker = self.sample()
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "REALTIME_QUOTE_VERIFIED")
        self.assertIsNone(result["max_entry"])
        self.assertIsNone(result["stop"])
        self.assertFalse(result["execution_authorized"])
        self.assertIn("策略", result["field_missing_reasons"]["買進觸發"])
        self.assertIn("費稅", result["field_missing_reasons"]["成本後RR"])

    def test_close_only_quote_cannot_be_accepted_as_live_trade(self):
        quote, ticker = self.sample()
        quote.pop("lastPrice")
        quote["closePrice"] = 92.2
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "INVALID_OR_MISSING_PRICE")
        self.assertIsNone(result["last_price"])
        self.assertFalse(result["execution_authorized"])

    def test_missing_lasttrade_time_keeps_observation_without_live_certification(self):
        quote, ticker = self.sample()
        quote.pop("lastTrade")
        quote["closeTime"] = epoch_us(NOW)
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "UNVERIFIED_EXECUTION_TIME")
        self.assertEqual(result["observed_price"], 92.2)
        self.assertIsNone(result["last_trade_tpe"])
        self.assertFalse(result["executed_trade_verified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["live_order_enabled"])

    def test_holding_trade_evidence_independent_of_new_daytrade_eligibility(self):
        quote, ticker = self.sample()
        quote["lastTrade"]["price"] = 850.0
        quote["lastPrice"] = 850.0
        ticker["canDayTrade"] = False
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("2330", NOW)
        self.assertEqual(result["status"], "DAY_TRADE_NOT_ELIGIBLE")
        self.assertTrue(result["position_trade_observed"])
        self.assertEqual(result["last_trade_price"], 850.0)
        self.assertFalse(result["executed_trade_verified"])
        self.assertFalse(result["execution_authorized"])

    def test_lastprice_fallback_never_claims_actual_position_trade(self):
        quote, ticker = self.sample()
        quote["lastTrade"].pop("price", None)
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("2330", NOW)
        self.assertFalse(result["position_trade_observed"])
        self.assertIsNone(result["last_trade_price"])

    def test_stale_quote_fail_closed(self):
        quote, ticker = self.sample(minutes=5)
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "STALE_QUOTE")

    def test_no_day_trade(self):
        quote, ticker = self.sample()
        ticker["canDayTrade"] = False
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "DAY_TRADE_NOT_ELIGIBLE")

    def test_duplicate_paid_endpoint_is_explicit_but_still_fail_closed(self):
        with patch("src.sky_single_stock_realtime.fugle.get_quote",
                   side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
            result = collect("3717", NOW)
        self.assertEqual(result["status"], "QUOTE_FETCH_FAILED")
        self.assertEqual(result["block_reason"], "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["live_order_enabled"])
        self.assertIsNone(result["entry_trigger"])

    def test_arbitrary_provider_errors_do_not_leak_into_receipt(self):
        with patch("src.sky_single_stock_realtime.fugle.get_quote",
                   side_effect=RuntimeError("secret-provider-details")):
            result = collect("3717", NOW)
        self.assertEqual(result["status"], "QUOTE_FETCH_FAILED")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertNotIn("block_reason", result)
        self.assertNotIn("secret-provider-details", str(result))

    def test_permission_failure(self):
        with patch("src.sky_single_stock_realtime.fugle.get_quote", side_effect=PermissionError()):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "QUOTE_FETCH_FAILED")


if __name__ == "__main__":
    unittest.main()
