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
