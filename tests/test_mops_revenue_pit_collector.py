import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.collect_mops_revenue_pit import (
    append_dedup_jsonl,
    parse_revenue_filings,
    roc_date_to_iso_date,
)


def _fixture():
    return """
    <html><body>
      <div>最後更新時間 115/10/12 12:57:15</div>
      <table>
        <tr><th>公司代號</th><th>公司簡稱</th><th>發布時間</th><th>主旨</th></tr>
        <tr><td>6111</td><td>光聚晶電</td><td>11:57</td><td>11509-營業收入資訊</td></tr>
        <tr><td>6741</td><td>91APP*-KY</td><td>11:26</td><td>11509-營業收入資訊</td></tr>
        <tr><td>2412</td><td>中華電</td><td>12:23</td><td>11402-IFRSs資產負債表</td></tr>
      </table>
    </body></html>
    """


def test_roc_date_conversion():
    assert roc_date_to_iso_date("115/10/12") == "2026-10-12"


def test_parse_company_level_revenue_filing_times():
    rows = parse_revenue_filings(
        _fixture(),
        observed_at="2026-10-12T13:00:00+08:00",
    )
    assert len(rows) == 2
    assert rows[0]["symbol"] == "6111"
    assert rows[0]["revenue_year"] == 2026
    assert rows[0]["revenue_month"] == 9
    assert rows[0]["filing_published_at"] == "2026-10-12T11:57:00+08:00"
    assert rows[0]["filing_timestamp_source"] == "MOPS_OFFICIAL"
    assert rows[0]["point_in_time_verified"] is True


def test_missing_page_date_is_rejected():
    page = "<table><tr><td>6111</td><td>11:57</td><td>11509-營業收入資訊</td></tr></table>"
    try:
        parse_revenue_filings(page)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_jsonl_dedup(tmp_path):
    rows = parse_revenue_filings(_fixture(), observed_at="2026-10-12T13:00:00+08:00")
    path = tmp_path / "ledger.jsonl"
    first = append_dedup_jsonl(path, rows)
    second = append_dedup_jsonl(path, rows)
    assert first["added"] == 2
    assert second["added"] == 0
    assert second["total"] == 2
