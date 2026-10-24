from src.data_contract import (
    candle_turnover_twd,
    fugle_lots_to_shares,
    registry_snapshot,
    validate_fugle_candle,
)

def test_fugle_lot_conversion():
    assert fugle_lots_to_shares(1) == 1000.0
    assert fugle_lots_to_shares(12.5) == 12500.0

def test_turnover_conversion():
    assert candle_turnover_twd(50.0, 20.0) == 1_000_000.0

def test_valid_candle():
    c = {"open": 50.0, "high": 51.0, "low": 49.5, "close": 50.5, "volume": 200.0}
    assert validate_fugle_candle(c) == []

def test_inconsistent_high_detected():
    c = {"open": 50.0, "high": 49.0, "low": 48.5, "close": 50.5, "volume": 200.0}
    assert "high_inconsistent" in validate_fugle_candle(c)

def test_contract_registry_units():
    reg = registry_snapshot()
    assert reg["volume_5m"]["unit"] == "lot"
    assert reg["volume_shares"]["unit"] == "share"
    assert reg["turnover"]["unit"] == "TWD"
    assert reg["timestamp"]["unit"] == "Asia/Taipei"
