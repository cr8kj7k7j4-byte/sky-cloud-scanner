from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest
from src.fugle_quote_validation import validate_fugle_quote

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=TPE)


def q(**updates):
    result = {"symbol": "6695", "lastPrice": 54.2, "isClose": False,
              "lastUpdated": int(NOW.timestamp() * 1_000_000)}
    result.update(updates)
    return result


def test_valid_fugle_live_quote():
    result = validate_fugle_quote(q(), "6695", now=NOW)
    assert result["status"] == "LIVE_QUOTE_VALID"
    assert result["price"] == 54.2


@pytest.mark.parametrize("payload,error", [
    (q(symbol="9914"), "FUGLE_SYMBOL_MISMATCH"),
    (q(lastPrice=None), "FUGLE_PRICE_MISSING"),
    (q(lastUpdated=None), "FUGLE_TIMESTAMP_MISSING"),
    (q(isClose=True), "FUGLE_MARKET_CLOSED"),
    (q(lastUpdated=int((NOW.timestamp() - 500) * 1_000_000)), "FUGLE_QUOTE_STALE"),
    (q(lastUpdated=int((NOW.timestamp() + 120) * 1_000_000)), "FUGLE_FUTURE_TIMESTAMP"),
])
def test_fail_closed(payload, error):
    with pytest.raises(ValueError, match=error):
        validate_fugle_quote(payload, "6695", now=NOW)


def test_after_hours_not_live():
    with pytest.raises(ValueError, match="OUTSIDE_REGULAR_MARKET_SESSION"):
        validate_fugle_quote(q(lastUpdated=int(datetime(2026, 10, 28, 14, 0, tzinfo=TPE).timestamp() * 1_000_000)),
                             "6695", now=datetime(2026, 10, 28, 14, 0, tzinfo=TPE))
