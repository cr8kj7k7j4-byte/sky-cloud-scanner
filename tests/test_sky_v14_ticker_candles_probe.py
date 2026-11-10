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
            "canDayTrade":True,"canBuyDayTrade":True,
            "securityStatus":"NORMAL","limitUpPrice":33,
            "tradingCurrency":"TWD",
            "isDisposition":False,"isAttention":False,"isSpecificAbnormally":False}

def candles(symbol,timeframe="5"):
    return {"date":"2026-11-10","timeframe":"5","data":[
        {"date":f"2026-11-10T{10+i//12:02d}:{(i%12)*5:02d}:00+08:00",
         "close":30+i*0.01,"volume":100} for i in range(6)]}

class DeepFiveMinTests(unittest.TestCase):
    def test_balanced_two_market_provenance_without_trade(self):
        x=run(stage2(),ticker_fn=ticker,candle_fn=candles,sleep_fn=lambda _:None,now=NOW)
        self.assertEqual(x["attempted_api_requests"],4)
        self.assertEqual(len(x["samples"]),2)
        self.assertTrue(all(z["valid_today_five_min_bars"]==6 for z in x["samples"]))
        self.assertTrue(all(z["status"]=="CANDLE_TICKER_RESEARCH_READY_NOT_TRADE" for z in x["samples"]))
        self.assertFalse(x["official_v14_entry_eligible"])
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
        self.assertTrue(all(z["status"]=="INCOMPLETE_TICKER_OR_5M_EVIDENCE" for z in x["samples"]))
    def test_no_trade_even_if_all_inputs_present(self):
        x=run(stage2(),ticker_fn=ticker,candle_fn=candles,sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["production_eligible"] is False for z in x["samples"]))


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
                            for z in x["samples"]))

    def test_current_unfinished_bar_excluded_from_features(self):
        def unfinished(symbol,timeframe="5"):
            q=candles(symbol,timeframe)
            q["data"].append({"date":"2026-11-10T11:14:00+08:00",
                              "close":90,"volume":100})
            return q
        x=run(stage2(),ticker_fn=ticker,candle_fn=unfinished,
              sleep_fn=lambda _:None,now=NOW)
        self.assertTrue(all(z["valid_today_five_min_bars"]==6
                            and z["excluded_unfinished_five_min_bars"]==1
                            and z["last_feature_bar_time_tpe"]=="2026-11-10T10:25:00+08:00"
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
                                for z in x["samples"]))

if __name__=="__main__":
    unittest.main()
