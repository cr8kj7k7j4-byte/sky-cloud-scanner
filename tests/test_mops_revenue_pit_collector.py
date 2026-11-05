import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.collect_mops_revenue_pit import (
    append_dedup_jsonl,
    parse_api_response,
    roc_datetime_to_iso,
)


def _payload(data):
    return {
        "code": 200,
        "message": "查詢成功",
        "result": {"data": data, "moreInfoUrl": "https://example.invalid"},
        "datetime": "115/10/25 13:55:27",
    }


def test_roc_datetime_conversion():
    assert roc_datetime_to_iso("115/10/25 13:55:27") == (
        "2026-10-25T13:55:27+08:00"
    )


def test_empty_official_response_is_valid_no_event():
    assert parse_api_response(
        _payload([]),
        market_kind="sii",
        observed_at="2026-10-25T13:56:00+08:00",
    ) == []


def test_parse_dict_shaped_revenue_row():
    payload = _payload([
        {
            "companyId": "6111",
            "companyName": "光聚晶電",
            "releaseTime": "11:57",
            "subject": "11509-營業收入資訊",
        }
    ])
    rows = parse_api_response(
        payload,
        market_kind="otc",
        observed_at="2026-10-25T13:56:00+08:00",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "6111"
    assert row["name"] == "光聚晶電"
    assert row["market"] == "TPEx"
    assert row["revenue_year"] == 2026
    assert row["revenue_month"] == 9
    assert row["filing_published_at"] == "2026-10-25T11:57:00+08:00"
    assert row["filing_timestamp_source"] == "MOPS_OFFICIAL"
    assert row["point_in_time_verified"] is True


def test_parse_nested_list_row():
    payload = _payload({
        "items": [
            ["6741", "91APP*-KY", "11:26", "11509-營業收入資訊"]
        ]
    })
    rows = parse_api_response(payload, market_kind="otc")
    assert len(rows) == 1
    assert rows[0]["symbol"] == "6741"
    assert rows[0]["name"] == "91APP*-KY"


def test_non_revenue_subject_is_ignored():
    payload = _payload([
        {
            "companyId": "2412",
            "companyName": "中華電",
            "releaseTime": "12:23",
            "subject": "11503-IFRSs資產負債表",
        }
    ])
    assert parse_api_response(payload, market_kind="sii") == []


def test_rejected_market_response_fails_closed():
    payload = {
        "code": 500,
        "message": "市場別格式有誤",
        "result": None,
        "datetime": "115/10/25 13:55:27",
    }
    try:
        parse_api_response(payload, market_kind="sii")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_jsonl_dedup(tmp_path):
    payload = _payload([
        ["6111", "光聚晶電", "11:57", "11509-營業收入資訊"]
    ])
    rows = parse_api_response(payload, market_kind="otc")
    path = tmp_path / "ledger.jsonl"
    first = append_dedup_jsonl(path, rows)
    second = append_dedup_jsonl(path, rows)
    assert first["added"] == 1
    assert second["added"] == 0
    assert second["total"] == 1


def test_mops_transient_non_json_recovery(monkeypatch):
    import io
    import research.collect_mops_revenue_pit as collector

    class FakeResponse:
        def __init__(self, content):
            self.content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, n=-1):
            return self.content[:n]

    attempts = []
    response = iter([b"<html>temporarily unavailable</html>",
                     b'{"code":200,"result":{"data":[]},"datetime":"115/11/05 12:05:00"}'])
    def fake_open(req, timeout=20):
        attempts.append(timeout)
        return FakeResponse(next(response))
    monkeypatch.setattr(collector.urllib.request, "urlopen", fake_open)
    sleeps = []
    result = collector.fetch_json_post("https://example.invalid", {"count": 5},
                                       attempts=3, sleeper=sleeps.append)
    assert result["code"] == 200
    assert len(attempts) == 2
    assert sleeps == [1]


def test_mops_persistent_bad_body_fails_closed(monkeypatch):
    import pytest
    import research.collect_mops_revenue_pit as collector
    class BadResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, n=-1): return b""
    monkeypatch.setattr(collector.urllib.request, "urlopen",
                        lambda req, timeout=20: BadResponse())
    slept = []
    with pytest.raises(RuntimeError, match="MOPS fetch failed after 3 attempts"):
        collector.fetch_json_post("https://example.invalid", {"count": 5},
                                  sleeper=slept.append)
    assert slept == [1, 2]


def test_mops_failures_leave_ledger_unchanged_and_create_snapshot(monkeypatch, tmp_path):
    import research.collect_mops_revenue_pit as collector
    import pytest
    monkeypatch.setattr(collector, "collect_all_markets",
                        lambda count=500: (_ for _ in ()).throw(RuntimeError("MOPS unreachable")))
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"keep":"existing"}\\n', encoding="utf-8")
    snapshot = tmp_path / "failure.json"
    monkeypatch.setattr(sys, "argv", ["collect_mops_revenue_pit.py",
                         "--out", str(ledger), "--snapshot", str(snapshot)])
    with pytest.raises(SystemExit, match="PIT ledger unchanged"):
        collector.main()
    assert ledger.read_text(encoding="utf-8") == '{"keep":"existing"}\\n'
    import json
    data = json.loads(snapshot.read_text())
    assert data["collection_status"] == "SOURCE_UNAVAILABLE"
    assert data["point_in_time_verified"] is False
    assert data["records"] == []
