"""Regression coverage for opt-in Fugle live-quote path."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src import fugle

TZ = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 10, 28, 10, 0, tzinfo=TZ)


def quote(**overrides):
    data = {
        "symbol": "6695", "lastPrice": 54.2, "isClose": False,
        "lastUpdated": int(NOW.timestamp() * 1_000_000)
    }
    data.update(overrides)
    return data


def test_validated_quote_fetches_and_exposes_provenance(monkeypatch):
    monkeypatch.setattr(fugle, "get_quote", lambda symbol: quote())
    result = fugle.get_validated_live_quote("6695", now=NOW)
    assert result["quote"]["lastPrice"] == 54.2
    assert result["validation"]["status"] == "LIVE_QUOTE_VALID"
    assert result["validation"]["symbol"] == "6695"


def test_validated_quote_blocks_closed_market(monkeypatch):
    monkeypatch.setattr(fugle, "get_quote", lambda symbol: quote(isClose=True))
    with pytest.raises(ValueError, match="FUGLE_MARKET_CLOSED"):
        fugle.get_validated_live_quote("6695", now=NOW)


def test_validated_quote_blocks_symbol_mismatch(monkeypatch):
    monkeypatch.setattr(fugle, "get_quote", lambda symbol: quote(symbol="9914"))
    with pytest.raises(ValueError, match="FUGLE_SYMBOL_MISMATCH"):
        fugle.get_validated_live_quote("6695", now=NOW)


def test_legacy_quote_is_unmodified_and_does_not_invoke_gate(monkeypatch):
    monkeypatch.setattr(fugle, "_get", lambda path, params=None: {"path": path})
    assert fugle.get_quote("6695") == {"path": "/intraday/quote/6695"}
