from src.sector_membership_events import (
    parse_sector_change_text,
    reconstruct_effective_sector_intervals,
)


def test_parse_tpex_style_sector_change_announcement():
    text = """
    主旨：公告調整部分上櫃公司產業類別，自115年6月1日起實施。
    (一)川寶科技股份有限公司（股票代號：1595）由「電子零組件業」調整為「半導體業」。
    (二)泰茂實業股份有限公司（股票代號：2230）由「電機機械」調整為「居家生活」。
    """
    out = parse_sector_change_text(text, exchange="TPEx")
    assert len(out) == 2
    assert out[0].symbol == "1595"
    assert out[0].old_sector == "電子零組件業"
    assert out[0].new_sector == "半導體業"
    assert out[0].effective_date == "2026-06-01"


def test_reconstruct_intervals_backwards_from_current_sector():
    current = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "name": "川寶",
        "sector": "半導體業",
        "listed_from": "2010-01-01",
        "source_as_of": "2026-10-25",
    }]
    events = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "old_sector": "電子零組件業",
        "new_sector": "半導體業",
        "effective_date": "2026-06-01",
        "source_url": "u",
        "source_as_of": "2026-05-19",
        "notes": "",
    }]
    out = reconstruct_effective_sector_intervals(current, events)
    assert out["production_eligible"] is True
    assert out["unresolved"] == []
    assert out["intervals"] == [
        {
            "symbol": "1595",
            "exchange": "TPEx",
            "name": "川寶",
            "sector": "電子零組件業",
            "effective_from": "2010-01-01",
            "effective_to": "2026-05-31",
            "source": "official_sector_event_ledger",
            "source_as_of": "2026-10-25",
        },
        {
            "symbol": "1595",
            "exchange": "TPEx",
            "name": "川寶",
            "sector": "半導體業",
            "effective_from": "2026-06-01",
            "effective_to": None,
            "source": "official_sector_event_ledger",
            "source_as_of": "2026-10-25",
        },
    ]


def test_chain_mismatch_fails_closed():
    current = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "sector": "其他",
        "listed_from": "2010-01-01",
    }]
    events = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "old_sector": "電子零組件業",
        "new_sector": "半導體業",
        "effective_date": "2026-06-01",
        "source_url": "",
        "source_as_of": "",
        "notes": "",
    }]
    out = reconstruct_effective_sector_intervals(current, events)
    assert out["production_eligible"] is False
    assert out["unresolved"][0]["reason"] == "EVENT_CHAIN_NEW_SECTOR_MISMATCH"


def test_unknown_old_sector_preserves_post_change_interval_but_stops_history():
    current = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "name": "川寶",
        "sector": "半導體業",
        "listed_from": "2010-01-01",
        "source": "current",
        "source_as_of": "2026-10-25",
    }]
    events = [{
        "symbol": "1595",
        "exchange": "TPEx",
        "old_sector": None,
        "new_sector": "半導體業",
        "effective_date": "2026-06-01",
        "source_url": "official",
        "source_as_of": "2026-05-19",
        "notes": "old sector unavailable",
    }]
    out = reconstruct_effective_sector_intervals(current, events)
    assert out["production_eligible"] is False
    assert out["unresolved"][0]["reason"] == "PRE_CHANGE_SECTOR_UNKNOWN"
    assert out["intervals"] == [{
        "symbol": "1595",
        "exchange": "TPEx",
        "name": "川寶",
        "sector": "半導體業",
        "effective_from": "2026-06-01",
        "effective_to": None,
        "source": "official_sector_event_ledger",
        "source_url": "official",
        "source_as_of": "2026-05-19",
    }]


def test_parser_extracts_effective_date_with_whitespace():
    text = """
    主旨：調整部分上櫃公司產業類別，自 115年 6月 1日 起實施。
    股票代號：1595 由「電子零組件業」調整為「半導體業」
    """
    out = parse_sector_change_text(text, exchange="TPEx")
    assert out[0].effective_date == "2026-06-01"
