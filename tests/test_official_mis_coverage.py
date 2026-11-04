from src import official

class Response:
    def __init__(self, arr): self.arr=arr
    def raise_for_status(self): pass
    def json(self): return {"msgArray": self.arr}

class FakeSession:
    def __init__(self): self.headers={}; self.calls=[]
    def get(self,url,params=None,timeout=20):
        if params is None: return Response([])
        symbols=[v.split("_")[1].split(".")[0] for v in params["ex_ch"].split("|")]
        self.calls.append(symbols)
        # Simulate silent truncation of large MIS requests.
        returned=symbols[:2] if len(symbols)>8 else symbols
        return Response([{"c":s,"z":"30","y":"29","v":"1000","h":"31","l":"29","o":"30"} for s in returned])

def test_mis_truncation_recovers_missing_symbols(monkeypatch):
    fake=FakeSession()
    monkeypatch.setattr(official,"session",lambda:fake)
    monkeypatch.setattr(official.time,"sleep",lambda _:None)
    universe=[{"symbol":str(1000+i),"name":"x","exchange":"TWSE","mis_prefix":"tse"} for i in range(40)]
    rows,warnings=official.fetch_mis_quotes(universe,batch_size=40)
    assert len(rows)==40
    assert len({r["symbol"] for r in rows})==40
    assert any("recovery_requested=38" in x for x in warnings)
    assert not any("MIS_LOW_COVERAGE" in x for x in warnings)

def test_mis_missing_stays_missing_instead_of_fabricating(monkeypatch):
    class EmptySession(FakeSession):
        def get(self,url,params=None,timeout=20):
            if params is None: return Response([])
            return Response([])
    monkeypatch.setattr(official,"session",lambda:EmptySession())
    monkeypatch.setattr(official.time,"sleep",lambda _:None)
    universe=[{"symbol":"2330","name":"x","exchange":"TWSE","mis_prefix":"tse"}]
    rows,warnings=official.fetch_mis_quotes(universe)
    assert rows==[]
    assert any("MIS_LOW_COVERAGE" in x for x in warnings)

def test_bulk_snapshot_prefers_last_executed_trade(monkeypatch):
    from src import fugle
    def fake(market):
        if market=="TSE":
            return {"date":"2026-11-03","data":[
                {"symbol":"2330","name":"台積電","lastPrice":100,"closePrice":101,
                 "tradeVolume":100,"tradeValue":10000000,"change":1,
                 "highPrice":102,"lowPrice":99,"openPrice":100,"lastUpdated":123}]}
        return {"date":"2026-11-03","data":[
            {"symbol":"6488","lastPrice":80,"tradeVolume":50,"tradeValue":4000000,
             "change":-1,"openPrice":81}]}
    monkeypatch.setattr(fugle,"snapshot_quotes",fake)
    universe=[
        {"symbol":"2330","market":"TSE","exchange":"TWSE"},
        {"symbol":"6488","market":"OTC","exchange":"TPEx"},
    ]
    rows,warnings=official.fetch_fugle_snapshot_quotes(universe,trading_date="2026-11-03")
    assert len(rows)==2
    assert rows[0]["last"]==100
    assert rows[0]["previous_close"]==99
    assert rows[1]["last"]==80
    assert rows[1]["previous_close"]==81

def test_bulk_snapshot_rejects_stale_or_untraded(monkeypatch):
    from src import fugle
    monkeypatch.setattr(fugle,"snapshot_quotes",lambda m:
        {"date":"2026-11-02","data":[{"symbol":"2330","lastPrice":100,"tradeVolume":100}]})
    rows,warnings=official.fetch_fugle_snapshot_quotes(
        [{"symbol":"2330","market":"TSE"}],trading_date="2026-11-03")
    assert rows==[]
    assert any("STALE" in w for w in warnings)


def test_mis_blank_z_retries_in_small_batch(monkeypatch):
    class BlankOnLargeBatch(FakeSession):
        def get(self, url, params=None, timeout=20):
            if params is None:
                return Response([])
            symbols=[v.split("_")[1].split(".")[0] for v in params["ex_ch"].split("|")]
            self.calls.append(symbols)
            rows=[]
            for sym in symbols:
                # Actual failure mode: each code is in msgArray, but z is '-'
                # for large requests. Its old code did NOT retry these rows.
                rows.append({"c":sym,"z":"-" if len(symbols)>8 else "30",
                             "y":"29","v":"1000","h":"31","l":"29","o":"30"})
            return Response(rows)
    fake=BlankOnLargeBatch()
    monkeypatch.setattr(official,"session",lambda:fake)
    monkeypatch.setattr(official.time,"sleep",lambda _:None)
    universe=[{"symbol":str(2000+i),"name":"x","exchange":"TWSE","mis_prefix":"tse"} for i in range(24)]
    rows,warnings=official.fetch_mis_quotes(universe,batch_size=24)
    assert len(rows)==24
    assert len(fake.calls)==4
    assert any("recovery_requested=24" in w for w in warnings)
    assert any("recovery_valid_quotes=24" in w for w in warnings)
    assert not any("MIS_LOW_COVERAGE" in w for w in warnings)

def test_mis_blank_z_without_recovery_stays_missing(monkeypatch):
    class AlwaysBlank(FakeSession):
        def get(self, url, params=None, timeout=20):
            if params is None:
                return Response([])
            symbols=[v.split("_")[1].split(".")[0] for v in params["ex_ch"].split("|")]
            return Response([{"c":sym,"z":"-","y":"30","v":"1000","h":"32","l":"29","o":"30"} for sym in symbols])
    monkeypatch.setattr(official,"session",lambda:AlwaysBlank())
    monkeypatch.setattr(official.time,"sleep",lambda _:None)
    universe=[{"symbol":"2330","name":"x","exchange":"TWSE","mis_prefix":"tse"}]
    rows,warnings=official.fetch_mis_quotes(universe)
    assert rows==[]
    assert any("recovery_requested=1" in w for w in warnings)
    assert any("MIS_LOW_COVERAGE" in w for w in warnings)
