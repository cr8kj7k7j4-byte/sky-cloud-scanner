"""Offline contracts only; do not call paid market API or live GCS."""
from datetime import date, datetime, timezone, timedelta
import json
import pytest
from research.three_model_next_session_markout import (
    run, validate_observation, first_next_session, create_only,
    OBS_PREFIX, OUTCOME_PREFIX,
)

class PreconditionFailed(Exception):
    pass

class Object:
    def __init__(self, db, name):
        self.db, self.name = db, name
    def download_as_bytes(self):
        return self.db[self.name]
    def upload_from_string(self, data, *, if_generation_match, content_type):
        assert if_generation_match == 0
        assert content_type == "application/json"
        if self.name in self.db:
            raise PreconditionFailed()
        self.db[self.name] = data

class Bucket:
    def __init__(self, db):
        self.db = db
    def blob(self, key):
        return Object(self.db, key)

class Storage:
    def __init__(self, obs):
        self.db = {}
        for x in obs:
            key = f"{OBS_PREFIX}{x['model_id']}/{x['symbol']}/{x['ledger_record_id']}.json"
            self.db[key] = json.dumps(x, ensure_ascii=False).encode()
    def list_blobs(self, name, *, prefix, max_results):
        assert name == "test-private-ledger"
        assert prefix == OBS_PREFIX
        return [Object(self.db, k) for k in self.db if k.startswith(prefix)][:max_results]
    def bucket(self, name):
        assert name == "test-private-ledger"
        return Bucket(self.db)

def obs(rid="rejected-123456789012345678901234", direction="NO_TRADE",
        stamp="2026-11-05T13:30:00+08:00", reference=26.75):
    return {"ledger_record_id":rid, "model_id":"next_day", "symbol":"1101",
            "bar_time":stamp,"reference_close":reference,"direction":direction,
            "production_signal":False,"order_authorized":False,
            "eligible_strategy_trade":False,"trained_model_used":False}

def fake_candles(symbol, tf, start, end, key):
    assert (symbol, tf, key) == ("1101","D","test-key")
    assert start == date(2026,11,6)
    assert end == date(2026,11,6)
    return [{"timestamp":"2026-11-06T13:30:00+08:00","close":27.0}]

def test_next_session_real_market_time_and_no_trade_pnl_claim():
    item = validate_observation(obs())
    outcome = first_next_session(item, fake_candles("1101","D",date(2026,11,6),
                                                     date(2026,11,6),"test-key"))
    assert outcome["next_session_close_time"]=="2026-11-06T13:30:00+08:00"
    assert outcome["direction_at_observation"]=="NO_TRADE"
    assert outcome["actual_fill"] is False
    assert outcome["realized_net_pnl"] is None
    assert outcome["net_strategy_return"] is None
    assert outcome["production_signal"] is False

def test_pending_without_future_session_never_persists_price():
    store=Storage([obs()])
    result=run(store,"test-private-ledger","test-key",date(2026,11,5),
               fetch=lambda *args: [])
    assert result["completed_outcomes"]==0
    assert result["pending_count"]==1
    assert not any(k.startswith(OUTCOME_PREFIX) for k in store.db)

def test_next_session_create_only_readback_and_idempotent():
    store=Storage([obs()])
    first=run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=fake_candles)
    second=run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=fake_candles)
    assert first["new_outcomes"]==1 and second["already_exists_identical"]==1
    assert len([k for k in store.db if k.startswith(OUTCOME_PREFIX)])==1
    assert first["production_signal"] is False

def test_conflicting_later_market_data_fails_not_overwrites():
    store=Storage([obs()])
    run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=fake_candles)
    def mutated(*args):
        return [{"timestamp":"2026-11-06T13:30:00+08:00","close":99.0}]
    with pytest.raises(ValueError,match="immutable_followup_conflict"):
        run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=mutated)

def test_missing_time_is_pending_and_unsafe_claim_rejected():
    store=Storage([obs(stamp=None, reference=None)])
    r=run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=lambda *a: [])
    assert r["pending_count"]==1 and r["completed_outcomes"]==0
    with pytest.raises(ValueError,match="unsafe_record_claim"):
        validate_observation(dict(obs(),production_signal=True))

def test_duplicate_record_id_blocks_followup():
    store=Storage([obs()])
    extra=obs()
    extra["model_id"]="swing_3_20d"
    store.db[f"{OBS_PREFIX}swing_3_20d/1101/{extra['ledger_record_id']}.json"]=json.dumps(extra).encode()
    with pytest.raises(ValueError,match="duplicate_ledger_record_id"):
        run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=fake_candles)

def test_empty_provider_next_session_keeps_pending_instead_of_failing():
    store=Storage([obs()])
    def empty(*args):
        raise ValueError("provider_empty_data")
    result=run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=empty)
    assert result["completed_outcomes"]==0
    assert result["pending_count"]==1
    assert result["pending_reasons"][0]["reason"]=="NEXT_SESSION_CANDLE_NOT_AVAILABLE"

def test_provider_schema_error_is_not_silently_pending():
    store=Storage([obs()])
    def invalid(*args):
        raise ValueError("provider_symbol_or_timeframe_mismatch")
    with pytest.raises(ValueError,match="mismatch"):
        run(store,"test-private-ledger","test-key",date(2026,11,6),fetch=invalid)

def test_weekend_is_successful_audited_skip_no_paid_request():
    store=Storage([obs()])
    def forbidden(*args, **kwargs):
        raise AssertionError("weekend must not call paid Fugle API")
    result=run(store,"test-private-ledger","test-key",
               date(2026,11,8),fetch=forbidden)
    assert result["status"]=="SKIPPED_NO_COMPLETED_WEEKEND_SESSION"
    assert result["new_outcomes"]==0
    assert result["production_signal"] is False
    assert result["trading_enabled"] is False
    assert not any(k.startswith(OUTCOME_PREFIX) for k in store.db)


def test_friday_observation_tracks_monday_actual_session_not_weekend():
    store = Storage([obs(rid="friday-123456789012345678901234",
                         direction="LONG_WATCH",
                         stamp="2026-10-30T13:30:00+08:00", reference=30.0)])
    def monday_candles(symbol, tf, start, end, key):
        assert (symbol, tf, key) == ("1101", "D", "test-key")
        assert start == date(2026, 10, 31)
        assert end == date(2026, 11, 2)
        return [{"timestamp":"2026-11-02T13:30:00+08:00","close":30.6}]
    result = run(store, "test-private-ledger", "test-key",
                 date(2026, 11, 2), fetch=monday_candles)
    assert result["new_outcomes"] == 1
    key = next(k for k in store.db if k.startswith(OUTCOME_PREFIX))
    outcome = json.loads(store.db[key])
    assert outcome["ledger_record_id"] == "friday-123456789012345678901234"
    assert outcome["next_session_close_time"] == "2026-11-02T13:30:00+08:00"
    assert outcome["direction_at_observation"] == "LONG_WATCH"
    assert outcome["next_session_return_pct"] == 2.0
    assert outcome["actual_fill"] is False


def test_weekday_closure_with_no_provider_session_remains_pending():
    # A weekday alone does not prove that an exchange session occurred.
    store = Storage([obs(rid="holiday-123456789012345678901234",
                         stamp="2026-10-30T13:30:00+08:00")])
    def no_completed_session(*args):
        raise ValueError("provider_empty_data")
    result = run(store, "test-private-ledger", "test-key",
                 date(2026, 11, 2), fetch=no_completed_session)
    assert result["completed_outcomes"] == 0
    assert result["pending_count"] == 1
    assert result["pending_reasons"][0]["reason"] == "NEXT_SESSION_CANDLE_NOT_AVAILABLE"
    assert not any(k.startswith(OUTCOME_PREFIX) for k in store.db)
