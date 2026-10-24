from src.vwap_entry_replay import (
    anti_chase_components,
    attach_vwap_entry_to_trades,
    build_vwap_entry_records,
)


def test_vwap_distance_and_session_position_are_point_in_time():
    rows = [
        {
            "symbol": "2330",
            "as_of": "2026-01-02T10:15:00+08:00",
            "entry_price": 102.0,
            "vwap": 100.0,
            "session_low": 98.0,
            "session_high": 104.0,
            "rvol": 1.8,
            "spread_pct": 0.001,
        }
    ]
    rec = build_vwap_entry_records(rows)[0]
    assert round(rec.price_vs_vwap_pct, 6) == 0.02
    assert round(rec.session_position, 6) == round((102.0 - 98.0) / 6.0, 6)
    assert rec.rvol == 1.8


def test_missing_vwap_is_not_imputed():
    rows = [
        {"symbol": "2330", "as_of": "2026-01-02", "entry_price": 102.0, "vwap": None}
    ]
    assert build_vwap_entry_records(rows) == []


def test_attach_marks_missing_without_invention():
    recs = build_vwap_entry_records(
        [
            {
                "symbol": "2330",
                "as_of": "2026-01-02",
                "entry_price": 102.0,
                "vwap": 100.0,
            }
        ]
    )
    out = attach_vwap_entry_to_trades(
        [
            {"code": "2330", "entry_date": "2026-01-02"},
            {"code": "2317", "entry_date": "2026-01-02"},
        ],
        recs,
    )
    assert out[0]["vwap_entry_status"] == "OK"
    assert out[1]["vwap_entry_status"] == "MISSING"
    assert "vwap" not in out[1]


def test_anti_chase_components_do_not_use_outcome_fields():
    rec = {
        "price_vs_vwap_pct": 0.015,
        "session_position": 0.8,
        "rvol": 2.0,
        "spread_pct": 0.002,
        "base_net_R": 2.5,
        "exit_price": 150,
        "mfe": 0.3,
    }
    comp = anti_chase_components(rec)
    assert set(comp) == {
        "price_vs_vwap_pct",
        "session_position",
        "rvol",
        "spread_pct",
    }
    assert "base_net_R" not in comp
    assert "exit_price" not in comp
