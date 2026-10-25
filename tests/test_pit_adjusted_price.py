from src.pit_adjusted_price import adjusted_bars_asof, adjustment_factor_for_bar


def _payload():
    return {
        "adjustment_capability": "PIT_ASOF_EVENT_LEDGER",
        "corporate_action_events": [
            {"date": "2024-06-24", "dataset": "TaiwanStockDividendResult", "ratio": 0.96},
            {"date": "2025-06-18", "dataset": "TaiwanStockSplitPrice", "ratio": 0.25},
        ],
        "data": [
            {"date": "2024-06-21", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
            {"date": "2024-06-24", "open": 97, "high": 99, "low": 96, "close": 98, "volume": 11},
            {"date": "2025-06-18", "open": 30, "high": 31, "low": 29, "close": 30, "volume": 12},
        ],
    }


def test_future_event_is_not_used_before_it_exists():
    p = _payload()
    rows = adjusted_bars_asof(p, "2024-06-21")
    assert len(rows) == 1
    assert rows[0]["close"] == 101
    assert rows[0]["adjustment_factor"] == 1.0


def test_event_adjusts_prior_bar_only_when_known():
    p = _payload()
    rows = adjusted_bars_asof(p, "2024-06-24")
    assert round(rows[0]["close"], 8) == round(101 * 0.96, 8)
    assert rows[1]["close"] == 98
    assert rows[1]["adjustment_factor"] == 1.0


def test_later_split_not_used_at_earlier_asof():
    assert adjustment_factor_for_bar(
        "2024-06-21",
        "2024-12-31",
        _payload()["corporate_action_events"],
    ) == 0.96


def test_no_forward_fill_or_synthetic_bar():
    p = _payload()
    rows = adjusted_bars_asof(p, "2024-06-23")
    assert [x["date"] for x in rows] == ["2024-06-21"]
