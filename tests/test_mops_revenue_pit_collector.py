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
