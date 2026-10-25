from src.feature_registry import (
    FEATURE_REGISTRY,
    FEATURE_REGISTRY_VERSION,
    registry_snapshot,
    validate_feature_names,
    validate_registry,
)
from src.feature_store import build_feature_envelope

def _features():
    return {
        "momentum_1": 0.5,
        "momentum_5": 2.0,
        "volume_ratio": 1.8,
        "vwap_distance_pct": 0.6,
        "intraday_range_pct": 3.2,
        "volatility_5": 1.1,
        "relative_strength": 1.4,
    }

def test_registry_is_complete_and_valid():
    out = validate_registry()
    assert out["valid"] is True
    assert out["feature_count"] == 7
    assert FEATURE_REGISTRY_VERSION == "1.1.0"

def test_each_feature_has_required_governance_metadata():
    snap = registry_snapshot()
    fields = (
        "feature_id","name","version","formula","unit","source","lookback",
        "timestamp_semantics","frequency","missing_policy","normalization",
        "leakage_risk","owner","deprecation_status","production_status",
    )
    for name, item in snap.items():
        assert item["name"] == name
        for field in fields:
            assert str(item[field]).strip()

def test_feature_names_are_registered():
    out = validate_feature_names(_features())
    assert out["all_names_registered"] is True
    assert out["unregistered"] == []

def test_feature_store_embeds_registry_and_runtime_lineage():
    env = build_feature_envelope(
        "2409",
        _features(),
        as_of="2026-10-25T09:30:00+08:00",
        calculation_timestamp="2026-10-25T09:30:01+08:00",
        available_at="2026-10-25T09:30:01+08:00",
        source="test",
    )
    assert env.quality["feature_registry_version"] == FEATURE_REGISTRY_VERSION
    assert env.quality["unregistered_features"] == []
    assert env.quality["feature_versions"]["momentum_1"] == "1.0.0"
    assert env.quality["feature_ids"]["momentum_1"] == "P0F.MOMENTUM_1"
    assert env.calculation_timestamp
    assert env.available_at

def test_unregistered_feature_is_visible_not_silent():
    f = _features()
    f["mystery_alpha"] = 1.23
    env = build_feature_envelope("2409", f, source="test")
    assert env.quality["valid_schema"] is False
    assert env.quality["unregistered_features"] == ["mystery_alpha"]
