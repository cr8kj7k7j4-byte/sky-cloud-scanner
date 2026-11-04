from research.audit_swing_ca_candidate_ledger import normalize_roc_day, _rows, build_candidate_ledger
import json


def test_corporate_action_roc_dates():
    assert normalize_roc_day("115年10月23日") == "2026-10-23"
    assert normalize_roc_day("115/10/27") == "2026-10-27"
    assert normalize_roc_day("1151027") == "2026-10-27"


def test_twse_exrights_must_validate_query_range():
    bad={"stat":"OK","strDate":"20261104","endDate":"20261104","fields":[],"data":[]}
    try:
        _rows(bad,"TWSE_EXRIGHT_ALT_START")
    except ValueError:
        pass
    else:
        assert False


def test_tpex_capital_reduction_reference_is_not_automatically_adjusted():
    p={"stat":"ok","date":"20261023~20261104","tables":[{
        "fields":["恢復買賣日期","股票代號","最後交易日之收盤價格",
                  "減資恢復買賣開始日參考價格","減資原因"],
        "data":[["1151027","8047","44.4","53.45","彌補虧損"]],
    }]}
    rows=_rows(p,"TPEX_CAPITAL_REDUCTION_RESUME")
    assert rows[0]["symbol"]=="8047"
    assert rows[0]["event_kind"]=="CAPITAL_REDUCTION"
    assert rows[0]["candidate_backward_price_ratio"] > 1.0
