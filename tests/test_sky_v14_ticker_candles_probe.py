import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from src.sky_v14_ticker_candles_probe import selected,run

NOW=datetime(2026,11,10,11,15,tzinfo=ZoneInfo("Asia/Taipei"))

def stage2():
    return {"schema":"SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1",
            "results":[
              {"symbol":sym,"exchange":ex,"verified_trade_price":30.0,
               "executed_trade_verified":True,"microstructure":{
                    "turnover_gate_pass":True,"l1_spread_gate_pass":True,"average_price":29.5}}
              for sym,ex in [("2409","TWSE"),("5202","TPEx")]]}

def ticker(symbol):
    return {"date":"2026-11-10","boardLot":1000,
            "symbol":symbol,"exchange":"TWSE" if symbol=="2409" else "TPEx",
            "canDayTrade":True,"canBuyDayTrade":True,
            "securityStatus":"NORMAL","limitUpPrice":33,
            "tradingCurrency":"TWD",
            "isDisposition":False,"isAttention":False,"isSpecificAbnormally":False}

def candles(symbol,timeframe="5"):
    return {"date":"2026-11-10","timeframe":"5",
            "symbol":symbol,"exchange":"TWSE" if symbol=="2409" else "TPEx",
            "data":[
        {"date":f"2026-11-10T{10+i//12:02d}:{(i%12)*5:02d}:00+08:00",
         "close":30+i*0.01,"volume":100} for i in range(6)]}

class DeepFiveMinTests(unittest.TestCase):
    def test_invalid_price_or_volume_blocks_features(self):
        for field, value in (("close", -1), ("close", 0), ("close", float("nan")),
                             ("close", float("inf")), ("close", True),
                             ("volume", -1), ("volume", float("nan")),
                             ("volume", float("inf")), ("volume", True)):
            def invalid(symbol, timeframe="5"):
                q = candles(symbol, timeframe)
                q["data"][-1][field] = value
                return q
            x = run(stage2(), ticker_fn=ticker, candle_fn=invalid,
                    sleep_fn=lambda _: None, now=NOW)
            self.assertTrue(all(s["status"] == "INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                                and s["feature_preview"] is None
                                and not s["production_eligible"] for s in x["samples"]),
                            (field, value))
    def test_balanced_two_market_provenance_without_trade(self):
        x=run(stage2(),ticker_fn=ticker,candle_fn=candles,sleep_fn=lambda _:None,now=NOW)
        self.assertEqual(x["attempted_api_requests"],4)
        self.assertEqual(len(x["samples"]),2)
        self.assertTrue(all(z["valid_today_five_min_bars"]==6 for z in x["samples"]))
        self.assertTrue(all(z["status"]=="CANDLE_TICKER_RESEARCH_READY_NOT_TRADE" for z in x["samples"]))
        self.assertFalse(x["official_v14_entry_eligible"])
    def test_raw_receipt_is_bounded_and_keeps_observation_time(self):
        x=run(stage2(),ticker_fn=ticker,candle_fn=candles,
              sleep_fn=lambda _:None,now=NOW)
        self.assertEqual(x["data_receipt_kind"],"LIVE_ONLY_IF_PROVIDER_CONFIRMED")
        self.assertEqual(x["time_tpe"],NOW.isoformat())
        for sample in x["samples"]:
            self.assertEqual(sample["observation_time_tpe"],NOW.isoformat())
            self.assertTrue(sample["ticker_received_at_tpe"])
            self.assertTrue(sample["candles_received_at_tpe"])
            raw=sample["raw_five_min_candles"]
            self.assertEqual(raw["symbol"],sample["symbol"])
            self.assertEqual(raw["exchange"],sample["exchange"])
            self.assertEqual(raw["timeframe"],"5")
            self.assertEqual(len(raw["data"]),6)
            self.assertIn("date",raw["data"][0])
            self.assertIn("close",raw["data"][0])

    def test_readback_rejects_wrong_sha_and_run_id(self):
        from unittest.mock import patch
        from research.sky_512_artifact_validate import validate
        with patch.dict("os.environ", {"GITHUB_SHA": "sha512", "GITHUB_RUN_ID": "123"}):
            receipt=run(stage2(),ticker_fn=ticker,candle_fn=candles,
                        sleep_fn=lambda _:None,now=NOW)
        expected=validate(receipt,expected_sha="sha512",expected_run_id="123")
        self.assertFalse(expected["production_eligible"])
        self.assertEqual(expected["status"],
                         "ARTIFACT_DATA_READBACK_PASS_PENDING_PROVIDER_SEMANTICS")
        with self.assertRaisesRegex(ValueError,"SHA_MISMATCH"):
            validate(receipt,expected_sha="another",expected_run_id="123")
        with self.assertRaisesRegex(ValueError,"RUN_ID_MISMATCH"):
            validate(receipt,expected_sha="sha512",expected_run_id="456")

    def test_readback_rejects_tampered_candle_or_count(self):
        from unittest.mock import patch
        from research.sky_512_artifact_validate import validate
        with patch.dict("os.environ", {"GITHUB_SHA": "sha512", "GITHUB_RUN_ID": "123"}):
            receipt=run(stage2(),ticker_fn=ticker,candle_fn=candles,
                        sleep_fn=lambda _:None,now=NOW)
        receipt["samples"][0]["valid_today_five_min_bars"]+=1
        with self.assertRaisesRegex(ValueError,"BAR_COUNT_MISMATCH"):
            validate(receipt,expected_sha="sha512",expected_run_id="123")

    def test_attention_stock_cannot_pass_research_readiness(self):
        def attention(symbol):
            data=ticker(symbol)
            data["isAttention"]=True
            return data
        x=run(stage2(),ticker_fn=attention,candle_fn=candles,sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE" for z in x["samples"]))

    def test_old_candle_date_fails(self):
        def old(_,timeframe="5"):
            q=candles(_,timeframe);q["date"]="2026-11-09";return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=old,sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                            and z["feature_preview"] is None for z in x["samples"]))
    def test_no_trade_even_if_all_inputs_present(self):
        x=run(stage2(),ticker_fn=ticker,candle_fn=candles,sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["production_eligible"] is False for z in x["samples"]))


    def test_cross_symbol_or_exchange_fails_closed(self):
        for endpoint in ("ticker", "candles"):
            for field in ("symbol", "exchange"):
                for invalid_value in (None, "WRONG"):
                    def wrong_ticker(symbol):
                        t=ticker(symbol)
                        if endpoint=="ticker":
                            t[field]=invalid_value
                        return t
                    def wrong_candles(symbol,timeframe="5"):
                        c=candles(symbol,timeframe)
                        if endpoint=="candles":
                            c[field]=invalid_value
                        return c
                    x=run(stage2(),ticker_fn=wrong_ticker,candle_fn=wrong_candles,
                          sleep_fn=lambda _:None,now=NOW)
                    self.assertTrue(all(z["source_identity_matches"] is False
                                        and z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                                        and z["feature_preview"] is None
                                        and z["production_eligible"] is False
                                        for z in x["samples"]), (endpoint,field,invalid_value))

    def test_unknown_risk_flags_fail_closed(self):
        for flag in ("isDisposition", "isAttention", "isSpecificAbnormally"):
            for missing in (True, False):
                def uncertain(symbol):
                    data=ticker(symbol)
                    if missing:
                        del data[flag]
                    else:
                        data[flag]=None
                    return data
                x=run(stage2(),ticker_fn=uncertain,candle_fn=candles,
                      sleep_fn=lambda _:None,now=NOW)
                self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                                    for z in x["samples"]))

    def test_future_bar_cannot_enter_features(self):
        def future(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            q["data"].append({"date":"2026-11-10T11:30:00+08:00",
                              "close":90,"volume":100})
            return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=future,
              sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                            and z["rejected_future_five_min_bars"]==1
                            and z["feature_preview"] is None
                            for z in x["samples"]))

    def test_current_unfinished_bar_excluded_from_features(self):
        def unfinished(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            q["data"].append({"date":"2026-11-10T11:10:00+08:00",
                              "close":90,"volume":100})
            return q
        # 11:10 bar is on-grid but remains unfinished at 11:13.
        early=datetime(2026,11,10,11,13,tzinfo=ZoneInfo("Asia/Taipei"))
        x=run(stage2(),ticker_fn=ticker,candle_fn=unfinished,
              sleep_fn=lambda _:None,now=early)
        self.assertTrue(all(z["valid_today_five_min_bars"]==6
                            and z["excluded_unfinished_five_min_bars"]==1
                            and z["last_feature_bar_time_tpe"]=="2026-11-10T10:25:00+08:00"
                            for z in x["samples"]))

    def test_off_grid_five_minute_timestamp_fails_closed(self):
        for timestamp in ("2026-11-10T10:26:00+08:00",
                          "2026-11-10T10:25:01+08:00",
                          "2026-11-10T10:25:00.001+08:00"):
            def off_grid(symbol,timeframe="5"):
                q=candles(symbol,timeframe)
                q["data"][-1]["date"]=timestamp
                return q
            x=run(stage2(),ticker_fn=ticker,candle_fn=off_grid,
                  sleep_fn=lambda _:None,now=NOW)
            self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                                and z["bar_sequence_valid"] is False
                                and z["feature_preview"] is None
                                for z in x["samples"]), timestamp)

    def test_last_feature_bar_time_is_normalized_to_taipei(self):
        def utc_last_bar(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            # The source may use UTC even when other bars use Taipei offsets.
            q["data"][-1]["date"]="2026-11-10T02:25:00Z"
            return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=utc_last_bar,
              sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["bar_sequence_valid"] is True
                            and z["last_feature_bar_time_tpe"]=="2026-11-10T10:25:00+08:00"
                            and z["status"]=="CANDLE_TICKER_RESEARCH_READY_NOT_TRADE"
                            for z in x["samples"]))

    def test_missing_five_minute_bar_blocks_features(self):
        def missing_bar(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            # Simulate an otherwise ordered sequence with a missing 10:15 bar.
            q["data"].pop(3)
            return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=missing_bar,
              sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["valid_today_five_min_bars"]==5
                            and z["bar_sequence_valid"] is False
                            and z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                            and z["feature_preview"] is None
                            and z["production_eligible"] is False
                            for z in x["samples"]))

    def test_duplicate_and_out_of_order_bars_rejected(self):
        for anomaly in ("duplicate", "out_of_order"):
            def invalid(symbol,timeframe="5"):
                q=candles(symbol,timeframe)
                if anomaly=="duplicate":
                    q["data"].append(dict(q["data"][-1]))
                else:
                    q["data"][-1],q["data"][-2]=q["data"][-2],q["data"][-1]
                return q
            x=run(stage2(),ticker_fn=ticker,candle_fn=invalid,
                  sleep_fn=lambda _:None,now=NOW)
            self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
                                and z["bar_sequence_valid"] is False
                                and z["feature_preview"] is None
                                for z in x["samples"]))

    def test_1321_scan_excludes_1320_forming_bar(self):
        """A 13:21 observation cannot use the 13:20-13:25 candle.

        The earlier 2026-11-10 13:21 research receipt returned 53 bars, but
        its raw timestamps were not certified; this is a regression fixture,
        not a claim that the provider did or did not include an unfinished bar.
        """
        from datetime import timedelta
        now = datetime(2026, 11, 10, 13, 21, tzinfo=ZoneInfo("Asia/Taipei"))
        first = datetime(2026, 11, 10, 9, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        def intraday(symbol, timeframe="5"):
            q = candles(symbol, timeframe)
            q["data"] = [
                {"date": (first + timedelta(minutes=5*i)).isoformat(),
                 "close": 30.0, "volume": 100}
                for i in range(53)
            ]
            return q
        out = run(stage2(), ticker_fn=ticker, candle_fn=intraday,
                  sleep_fn=lambda _: None, now=now)
        for row in out["samples"]:
            self.assertEqual(row["valid_today_five_min_bars"], 52)
            self.assertEqual(row["excluded_unfinished_five_min_bars"], 1)
            self.assertEqual(row["rejected_future_five_min_bars"], 0)
            self.assertEqual(row["last_feature_bar_time_tpe"],
                             "2026-11-10T13:15:00+08:00")
            self.assertFalse(row["production_eligible"])

    def test_0905_scan_never_reads_0905_opening_bar(self):
        """At 09:05, only 09:00-09:05 may have completed; 09:05 starts next bar."""
        scan=datetime(2026,11,10,9,5,tzinfo=ZoneInfo("Asia/Taipei"))
        def opening(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            q["data"]=[
                {"date":"2026-11-10T09:00:00+08:00","close":30,"volume":100},
                {"date":"2026-11-10T09:05:00+08:00","close":90,"volume":100},
            ]
            return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=opening,
              sleep_fn=lambda _:None,now=scan)
        self.assertTrue(all(
            z["valid_today_five_min_bars"]==1
            and z["excluded_unfinished_five_min_bars"]==1
            and z["last_feature_bar_time_tpe"]=="2026-11-10T09:00:00+08:00"
            and z["feature_preview"] is None
            and z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE"
            and z["production_eligible"] is False
            for z in x["samples"]
        ))
        self.assertFalse(x["official_v14_entry_eligible"])

if __name__=="__main__":
    unittest.main()
