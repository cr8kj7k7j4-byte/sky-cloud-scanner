import json
from pathlib import Path

from research.collect_swing_pit_daily import _contains, _interval_for_day, _symbol_intervals


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
