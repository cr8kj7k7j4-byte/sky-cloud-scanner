from src.official_universe_events import (
    normalize_roc_date, parse_basic_records, parse_listing_html,
    parse_delisting_html, parse_tpex_delisting_payload,
    parse_twse_newlisting_payload, parse_tpex_newlisting_csv, build_intervals
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


def test_twse_delisting_title_row_shape():
    html = """<table>
    <tr><th colspan="3">終止上市公司</th></tr>
    <tr><th>終止上市日期</th><th>公司名稱</th><th>上市編號</th></tr>
    <tr><td>115年09月01日</td><td>三商壽</td><td>2867</td></tr>
    <tr><td>114年08月15日</td><td>測試公司</td><td>6288</td></tr>
    </table>"""
    out = parse_delisting_html(html, "TWSE", "u", "2026-10-25T00:00:00+08:00")
    assert [x.symbol for x in out] == ["2867", "6288"]
    assert out[0].event_date == "2026-09-01"


def test_tpex_delisting_json_payload():
    payload = {
        "stat": "ok",
        "date": "2023",
        "tables": [{
            "fields": [
                "股票代號",
                "公司名稱",
                "終止上櫃日期",
                "終止上櫃原因",
                "公司資料網址",
            ],
            "data": [[
                "4736",
                "泰博科技股份有限公司",
                "112-12-22",
                "測試原因",
                "https://mops.twse.com.tw/mops/#/web/t05st03",
            ]],
            "totalCount": 1,
        }],
    }
    out = parse_tpex_delisting_payload(
        payload,
        "https://www.tpex.org.tw/www/zh-tw/company/deListed",
        "2026-10-25T00:00:00+08:00",
    )
    assert len(out) == 1
    assert out[0].symbol == "4736"
    assert out[0].exchange == "TPEx"
    assert out[0].event_date == "2023-12-22"
    assert out[0].event_type == "DELIST"


def test_twse_newlisting_json_payload():
    payload = {
        "stat": "OK",
        "fields": [
            "公司代號",
            "公司簡稱",
            "股票上市買賣日期",
            "備註",
        ],
        "data": [[
            "4736",
            "泰博",
            "112.12.22",
            "櫃轉市",
        ]],
    }
    out = parse_twse_newlisting_payload(
        payload,
        "https://www.twse.com.tw/rwd/zh/company/newlisting",
        "2026-10-25T00:00:00+08:00",
    )
    assert len(out) == 1
    assert out[0].symbol == "4736"
    assert out[0].exchange == "TWSE"
    assert out[0].event_date == "2023-12-22"
    assert out[0].event_type == "LIST"


def test_tpex_newlisting_csv_payload():
    text = """112年截至12月底新上櫃公司一覽表
月份,公司代號,公司名稱,上櫃日期
"1","6865","偉康科技","2023/01/11"
"12","2949","欣新網","2023/12/15"
"""
    out = parse_tpex_newlisting_csv(
        text,
        "https://www.tpex.org.tw/www/zh-tw/company/applicantStatDl",
        "2026-10-25T00:00:00+08:00",
    )
    assert len(out) == 2
    assert out[0].symbol == "6865"
    assert out[0].exchange == "TPEx"
    assert out[0].event_date == "2023-01-11"
    assert out[1].event_date == "2023-12-15"


def test_multiple_list_records_without_delist_are_coalesced():
    from src.official_universe_events import UniverseEvent
    events = [
        UniverseEvent("2465","TWSE","麗臺","LIST","2001-09-17","a","u","t"),
        UniverseEvent("2465","TWSE","麗臺科技","LIST","2001-09-19","b","u","t"),
    ]
    out = build_intervals(events)
    assert out["unresolved"] == []
    assert len(out["intervals"]) == 1
    interval = out["intervals"][0]
    assert interval["listed_from"] == "2001-09-17"
    assert interval["listed_to"] is None
    assert "coalesced_list_records=2" in interval["notes"]


def test_delist_then_relist_creates_separate_membership_intervals():
    from src.official_universe_events import UniverseEvent
    events = [
        UniverseEvent("1111","TPEx","A","LIST","2000-01-01","a","u","t"),
        UniverseEvent("1111","TPEx","A","DELIST","2005-01-01","b","u","t"),
        UniverseEvent("1111","TPEx","A2","LIST","2010-01-01","c","u","t"),
    ]
    out = build_intervals(events)
    assert out["unresolved"] == []
    assert len(out["intervals"]) == 2
    assert out["intervals"][0]["listed_from"] == "2000-01-01"
    assert out["intervals"][0]["listed_to"] == "2005-01-01"
    assert out["intervals"][1]["listed_from"] == "2010-01-01"
    assert out["intervals"][1]["listed_to"] is None
