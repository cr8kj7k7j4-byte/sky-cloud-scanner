from research.collect_swing_pit_daily import (
    _adjustment_factor,
    _build_adjustment_events,
    _contains,
    _event_ratio,
    _interval_for_day,
    _symbol_intervals,
)


def test_interval_membership_and_market_transfer():
    pit = {
        "intervals": [
            {"symbol": "1234", "exchange": "TPEx", "listed_from": "2023-01-01", "listed_to": "2024-06-30"},
            {"symbol": "1234", "exchange": "TWSE", "listed_from": "2024-07-01", "listed_to": None},
        ]
    }
    by = _symbol_intervals(pit)
    assert _interval_for_day(by["1234"], "2024-06-30")[0]["exchange"] == "TPEx"
    assert _interval_for_day(by["1234"], "2024-07-01")[0]["exchange"] == "TWSE"
    assert _contains(by["1234"][0], "2022-12-31") is False


def test_dividend_backward_adjustment_ratio():
    row = {"before_price": 248.5, "reference_price": 240.5}
    ratio = _event_ratio("TaiwanStockDividendResult", row)
    assert round(ratio, 8) == round(240.5 / 248.5, 8)
    events = [{"date": "2019-06-24", "dataset": "TaiwanStockDividendResult", "ratio": ratio}]
    assert round(_adjustment_factor("2019-06-21", events), 8) == round(ratio, 8)
    assert _adjustment_factor("2019-06-24", events) == 1.0


def test_split_backward_adjustment_ratio():
    row = {"before_price": 170.15, "after_price": 24.3}
    ratio = _event_ratio("TaiwanStockSplitPrice", row)
    assert round(ratio, 8) == round(24.3 / 170.15, 8)


def test_same_day_multiple_corporate_actions_fail_closed():
    events, conflicts, invalid = _build_adjustment_events(
        "1234",
        {
            "TaiwanStockDividendResult": [
                {"date": "2025-07-01", "before_price": 100, "reference_price": 95}
            ],
            "TaiwanStockCapitalReductionReferencePrice": [
                {
                    "date": "2025-07-01",
                    "ClosingPriceonTheLastTradingDay": 100,
                    "PostReductionReferencePrice": 80,
                }
            ],
        },
    )
    assert events == []
    assert len(conflicts) == 1
    assert invalid == []
