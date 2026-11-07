from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError
import io
import json
import pytest

from research.three_model_fugle_pipeline import normalize_response, read_fugle, upload_immutable, run

TPE=timezone(timedelta(hours=8))
def candle(i,tf="D"):
    d=(date(2026,10,1)+timedelta(days=i)).isoformat()
    return {"date": d if tf=="D" else d+"T09:05:00+08:00", "open":30.0,
            "high":31.0,"low":29.0,"close":30.0,"volume":1000}

def test_fugle_schema_and_date_conversion():
    response={"symbol":"1101","timeframe":"D","data":[candle(1),candle(0)]}
    rows=normalize_response("1101","D",response,date(2026,10,1),date(2026,10,2))
    assert rows[0]["timestamp"]=="2026-10-01T13:30:00+08:00"
    assert len(rows)==2

def test_mismatch_and_out_of_range_rejected():
    row={"symbol":"WRONG","timeframe":"5","data":[candle(0,"5")]}
    with pytest.raises(ValueError,match="mismatch"):
        normalize_response("1101","5",row,date(2026,10,1),date(2026,10,2))
    row["symbol"]="1101"
    with pytest.raises(ValueError,match="outside"):
        normalize_response("1101","5",row,date(2026,11,1),date(2026,11,2))

def test_auth_must_be_present_before_request():
    with pytest.raises(RuntimeError,match="missing_fugle"):
        read_fugle("1101","D",date(2026,10,1),date(2026,10,3),"",get=lambda r: None)

class PreconditionFailed(Exception):
    pass
class Blob:
    def __init__(self,items,key):
        self.items=items;self.key=key
    def upload_from_string(self,data,**kwargs):
        assert kwargs["if_generation_match"]==0
        if self.key in self.items:
            raise PreconditionFailed()
        self.items[self.key]=data.encode()
    def download_as_bytes(self):
        return self.items[self.key]
class Bucket:
    def __init__(self,items): self.items=items
    def blob(self,key): return Blob(self.items,key)
class Storage:
    def __init__(self): self.items={}
    def bucket(self,name):
        assert name=="sky-private-research"
        return Bucket(self.items)

def report():
    return {"observations":[{"signal_id":"abc","model_id":"next_day","symbol":"1101",
                              "production_signal":False,"order_authorized":False}]}

def test_private_ledger_create_only_idempotent():
    store=Storage()
    first=upload_immutable(store,"sky-private-research","three-model/v1",report())
    second=upload_immutable(store,"sky-private-research","three-model/v1",report())
    assert first[0]["status"]=="CREATED"
    assert second[0]["status"]=="ALREADY_EXISTS_IDENTICAL"
    assert len(store.items)==1

def test_private_ledger_conflicting_record_rejected():
    store=Storage()
    upload_immutable(store,"sky-private-research","three-model/v1",report())
    changed=report()
    changed["observations"][0]["reference_close"]=999999
    with pytest.raises(ValueError,match="ledger_identity_conflict"):
        upload_immutable(store,"sky-private-research","three-model/v1",changed)

def test_missing_storage_blocked_before_api_calls(tmp_path):
    with pytest.raises(ValueError,match="invalid_symbol_count"):
        run([],date(2026,10,31),"sky-private-research","three-model/v1",
            "fake",Storage(),tmp_path/"out.json")

def test_rejected_decisions_are_stored_and_deduplicated():
    store=Storage()
    rejected={"observations":[{"signal_id":None,"model_id":"next_day",
        "symbol":"1101","direction":"NO_TRADE","rejection_reasons":["insufficient_bars"],
        "production_signal":False,"order_authorized":False}],
        "requested_end_date":"2026-11-06"}
    first=upload_immutable(store,"sky-private-research","three-model/v1",rejected)
    second=upload_immutable(store,"sky-private-research","three-model/v1",rejected)
    assert len(first)==len(second)==1
    assert first[0]["ledger_record_id"].startswith("rejected-")
    assert first[0]["signal_id"] is None
    assert second[0]["status"]=="ALREADY_EXISTS_IDENTICAL"
    assert len(store.items)==1
    assert json.loads(next(iter(store.items.values())))["eligible_strategy_trade"] is not True

def test_rejected_decisions_from_distinct_dates_not_collapsed():
    store=Storage()
    rejected={"observations":[{"signal_id":None,"model_id":"next_day",
        "symbol":"1101","direction":"NO_TRADE","rejection_reasons":["insufficient_bars"],
        "production_signal":False,"order_authorized":False}],
        "requested_end_date":"2026-11-06"}
    upload_immutable(store,"sky-private-research","three-model/v1",rejected)
    rejected["requested_end_date"]="2026-11-05"
    upload_immutable(store,"sky-private-research","three-model/v1",rejected)
    assert len(store.items)==2
