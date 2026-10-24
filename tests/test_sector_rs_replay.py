from src.sector_rs_replay import build_sector_rs, attach_sector_rs_to_trades


def test_sector_rs_is_point_in_time_and_relative():
    mapping = [
        {"symbol": "A", "sector": "S1", "effective_from": "2020-01-01"},
        {"symbol": "B", "sector": "S1", "effective_from": "2020-01-01"},
        {"symbol": "C", "sector": "S2", "effective_from": "2020-01-01"},
    ]
    returns = [
        {"symbol": "A", "as_of": "2026-01-02", "lookback_return": 0.10},
        {"symbol": "B", "as_of": "2026-01-02", "lookback_return": 0.00},
        {"symbol": "C", "as_of": "2026-01-02", "lookback_return": 0.03},
    ]
    rs = build_sector_rs(returns, mapping, {"2026-01-02": 0.02})
    by_symbol = {r.symbol: r for r in rs}

    assert round(by_symbol["A"].sector_return, 6) == 0.05
    assert round(by_symbol["A"].stock_rs_vs_sector, 6) == 0.05
    assert round(by_symbol["A"].sector_rs_vs_market, 6) == 0.03
    assert round(by_symbol["C"].sector_rs_vs_market, 6) == 0.01


def test_time_aware_sector_mapping():
    mapping = [
        {"symbol": "A", "sector": "OLD", "effective_from": "2020-01-01", "effective_to": "2025-12-31"},
        {"symbol": "A", "sector": "NEW", "effective_from": "2026-01-01"},
    ]
    returns = [
        {"symbol": "A", "as_of": "2025-12-30", "lookback_return": 0.10},
        {"symbol": "A", "as_of": "2026-01-02", "lookback_return": 0.20},
    ]
    rs = build_sector_rs(returns, mapping)
    assert [r.sector for r in rs] == ["OLD", "NEW"]


def test_attach_marks_missing_without_invention():
    mapping = [{"symbol": "A", "sector": "S", "effective_from": "2020-01-01"}]
    returns = [{"symbol": "A", "as_of": "2026-01-02", "lookback_return": 0.10}]
    rs = build_sector_rs(returns, mapping)
    out = attach_sector_rs_to_trades(
        [
            {"code": "A", "entry_date": "2026-01-02"},
            {"code": "B", "entry_date": "2026-01-02"},
        ],
        rs,
    )
    assert out[0]["sector_rs_status"] == "OK"
    assert out[1]["sector_rs_status"] == "MISSING"
    assert "sector" not in out[1]
