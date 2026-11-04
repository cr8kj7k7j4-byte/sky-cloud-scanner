from datetime import datetime
from zoneinfo import ZoneInfo

from research.sky_provider_readiness import provider_readiness

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 11, 4, 11, 30, tzinfo=TPE)


def test_403_entitlement_is_distinct_from_network_error():
    def denied(market):
        raise PermissionError("do not expose key")
    result = provider_readiness(
        now=NOW, snapshot_fetch=denied,
        single_quote_fetch=lambda symbol: {},
    )
    assert result["provider_status"] == "BLOCKED_PROVIDER_SNAPSHOT_ENTITLEMENT"
    assert result["markets"]["TSE"]["http_status"] == 403
    assert result["markets"]["OTC"]["snapshot_authorized"] is False
    assert result["whole_market_live_certified"] is False
    assert result["strategy_trade_authorized"] is False


def test_accessible_bulk_is_not_trade_timestamp_certification():
    def available(market):
        return {
            "date": "2026-11-04", "time": "113000",
            "data": [{"symbol": "1234", "lastPrice": 50,
                      "lastUpdated": int(NOW.timestamp() * 1000000),
                      "tradeVolume": 1500}],
        }
    result = provider_readiness(now=NOW, snapshot_fetch=available,
                                 single_quote_fetch=lambda symbol: {})
    assert result["provider_status"] == "BULK_SNAPSHOT_ACCESSIBLE_NOT_YET_MARKET_CERTIFIED"
    assert result["markets"]["TSE"]["non_trial_lastprice_with_volume"] == 1
    assert result["markets"]["TSE"]["trade_timestamp_per_symbol"] is False
    assert result["whole_market_live_certified"] is False


def test_trial_and_stale_are_rejected():
    def payload(market):
        return {
            "date": "2026-11-03", "time": "133000", "data": [
                {"lastPrice": 12, "tradeVolume": 400, "isTrial": True}
            ],
        }
    result = provider_readiness(now=NOW, snapshot_fetch=payload,
                                 single_quote_fetch=lambda symbol: {})
    assert result["provider_status"] == "BLOCKED_SNAPSHOT_SOURCE_OR_DATE"
    assert result["markets"]["TSE"]["non_trial_lastprice_with_volume"] == 0


def test_no_secret_or_raw_payload_in_report():
    secret = "SENSITIVE_TEST_KEY_123"
    def fail(market):
        raise RuntimeError(secret)
    result = provider_readiness(now=NOW, snapshot_fetch=fail,
                                 single_quote_fetch=lambda symbol: {})
    assert secret not in str(result)
