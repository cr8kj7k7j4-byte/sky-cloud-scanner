from src.official_universe_events import (
    normalize_roc_date, parse_basic_records, parse_listing_html,
    parse_delisting_html, build_intervals
)

def test_roc_dates():
    assert normalize_roc_date("115.10.16") == "2026-10-16"
    assert normalize_roc_date("114/08/15") == "2025-08-15"
    assert normalize_roc_date("2026-10-16") == "2026-10-16"
    assert normalize_roc_date("1121215") == "2023-12-15"
    assert normalize_roc_date("19960906") == "1996-09-06"

def test_basic_record_parser():
    rows=[{"公司代號":"2409","公司名稱":"友達","上市日期":"85.09.06"}]
    out=parse_basic_records(rows,"TWSE","u","2026-10-25T00:00:00+08:00")
    assert out[0].event_date=="1996-09-06"

def test_listing_html_parser():
    html="""<table><tr><th>公司代號</th><th>公司簡稱</th><th>股票上市買賣日期</th></tr>
    <tr><td>8908</td><td>欣雄</td><td>115.10.16</td></tr></table>"""
    out=parse_listing_html(html,"TWSE","u","2026-10-25T00:00:00+08:00")
    assert out[0].symbol=="8908"
    assert out[0].event_date=="2026-10-16"

def test_delisting_html_parser():
    html="""<table><tr><th>終止上市日期</th><th>公司名稱</th><th>上市編號</th></tr>
    <tr><td>114年08月15日</td><td>測試</td><td>6288</td></tr></table>"""
    out=parse_delisting_html(html,"TWSE","u","2026-10-25T00:00:00+08:00")
    assert len(out) == 1
    assert out[0].symbol == "6288"
    assert out[0].event_date == "2025-08-15"

def test_interval_build_and_fail_closed_unresolved():
    from src.official_universe_events import UniverseEvent
    e=[
      UniverseEvent("1111","TWSE","A","LIST","2020-01-01","s","u","t"),
      UniverseEvent("1111","TWSE","A","DELIST","2025-06-30","s","u","t"),
      UniverseEvent("2222","TPEx","B","DELIST","2025-06-30","s","u","t"),
    ]
    out=build_intervals(e)
    assert out["intervals"][0]["listed_to"]=="2025-06-30"
    assert out["unresolved"][0]["symbol"]=="2222"
