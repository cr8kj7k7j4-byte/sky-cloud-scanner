"""Offline-only W2 private GCS audit contracts: no credentials, no paid API."""
import hashlib
import json
import pytest

from research.three_model_private_ledger_audit import read_only_audit
from research.three_model_next_session_markout import OBS_PREFIX, OUTCOME_PREFIX

RID = "30ed67223d265d84dc0b7440"


class Blob:
    def __init__(self, name, body):
        self.name = name
        self.body = body
    def download_as_bytes(self):
        return self.body


class Store:
    def __init__(self, blobs):
        self.blobs = blobs
        self.write_calls = 0
    def list_blobs(self, bucket, *, prefix, max_results):
        assert bucket == "private-test-ledger"
        return [b for b in self.blobs if b.name.startswith(prefix)][:max_results]
    def bucket(self, *args):
        self.write_calls += 1
        raise AssertionError("read-only audit must never obtain a writable bucket")


def observation(**kwargs):
    row = dict(ledger_record_id=RID, signal_id=RID, model_id="next_day",
               symbol="1101", direction="LONG_WATCH",
               data_source="FUGLE", bar_time="2026-11-06T13:30:00+08:00",
               reference_close=28.4, production_signal=False,
               order_authorized=False, eligible_strategy_trade=False,
               trained_model_used=False)
    row.update(kwargs)
    return row


def outcome(**kwargs):
    row = dict(schema="sky-three-model-next-session-markout-v1",
               ledger_record_id=RID, symbol="1101", model_id="next_day",
               direction_at_observation="LONG_WATCH",
               observation_bar_time="2026-11-06T13:30:00+08:00",
               next_session_close_time="2026-11-09T13:30:00+08:00",
               next_session_close=28.6, next_session_return_pct=0.704225,
               actual_fill=False, trade_eligible=False,
               production_signal=False, trading_enabled=False,
               realized_net_pnl=None, net_strategy_return=None)
    row.update(kwargs)
    return row


def blob(prefix, row, name=None):
    key = name or f"{prefix}{row['model_id']}/{row['symbol']}/{row['ledger_record_id']}.json"
    return Blob(key, json.dumps(row).encode())


def test_original_signal_and_market_result_link_without_raw_prices():
    store = Store([blob(OBS_PREFIX, observation()), blob(OUTCOME_PREFIX, outcome())])
    report = read_only_audit(store, "private-test-ledger")
    assert report["observations_scanned"] == report["markouts_linked_to_original"] == 1
    assert report["pending_observations"] == 0
    assert report["observations"][0]["record_id"] == RID
    assert report["observations"][0]["direction"] == "LONG_WATCH"
    assert report["observations"][0]["bar_time_tpe"] == "2026-11-06T13:30:00+08:00"
    assert report["markouts"][0]["next_session_close_time_tpe"] == "2026-11-09T13:30:00+08:00"
    assert report["writes_performed"] is False and store.write_calls == 0
    assert "28.4" not in json.dumps(report) and "28.6" not in json.dumps(report)
    raw = store.blobs[0].body
    assert report["observations"][0]["object_sha256"] == hashlib.sha256(raw).hexdigest()


def test_missing_next_session_is_pending_not_successful_markout():
    report = read_only_audit(Store([blob(OBS_PREFIX, observation())]), "private-test-ledger")
    assert report["pending_observations"] == 1
    assert report["markouts_linked_to_original"] == 0


@pytest.mark.parametrize("bad,error", [
    ({"signal_id": "bad-id"}, "signal_ledger_id_mismatch"),
    ({"production_signal": True}, "unsafe_record_claim"),
    ({"data_source": "UNVERIFIED"}, "non_fugle_research_source"),
    ({"bar_time": "2026-11-06T13:30:00"}, "bar_time_without_timezone"),
])
def test_unsafe_or_broken_observation_blocks(bad, error):
    store = Store([blob(OBS_PREFIX, observation(**bad))])
    with pytest.raises(ValueError, match=error):
        read_only_audit(store, "private-test-ledger")


def test_tampered_object_key_rejected():
    store = Store([blob(OBS_PREFIX, observation(), f"{OBS_PREFIX}next_day/8088/{RID}.json")])
    with pytest.raises(ValueError, match="research_object_path_mismatch"):
        read_only_audit(store, "private-test-ledger")


def test_orphan_market_outcome_rejected():
    store = Store([blob(OUTCOME_PREFIX, outcome())])
    with pytest.raises(ValueError, match="orphan_markout_record"):
        read_only_audit(store, "private-test-ledger")


def test_mismatched_direction_rejected():
    store = Store([blob(OBS_PREFIX, observation()),
                   blob(OUTCOME_PREFIX, outcome(direction_at_observation="SHORT_WATCH"))])
    with pytest.raises(ValueError, match="markout_observation_identity_mismatch"):
        read_only_audit(store, "private-test-ledger")


def test_fake_future_or_pnl_blocked():
    with pytest.raises(ValueError, match="non_future_markout_session"):
        read_only_audit(Store([blob(OBS_PREFIX, observation()),
                               blob(OUTCOME_PREFIX, outcome(next_session_close_time="2026-11-06T13:30:00+08:00"))]),
                        "private-test-ledger")
    with pytest.raises(ValueError, match="unsafe_markout_pnl"):
        read_only_audit(Store([blob(OBS_PREFIX, observation()),
                               blob(OUTCOME_PREFIX, outcome(realized_net_pnl=500))]),
                        "private-test-ledger")


def test_scan_limit_fail_closed():
    store = Store([blob(OBS_PREFIX, observation()), blob(OBS_PREFIX, observation())])
    with pytest.raises(ValueError, match="ledger_scan_limit_reached"):
        read_only_audit(store, "private-test-ledger", max_scan=1)


def test_empty_private_bucket_is_not_successful_authentic_evidence():
    store = Store([])
    with pytest.raises(ValueError, match="no_research_observations_found"):
        read_only_audit(store, "private-test-ledger")
    assert store.write_calls == 0
