from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json

from .feature_registry import FEATURE_REGISTRY, FEATURE_REGISTRY_VERSION, validate_feature_names

FEATURE_SCHEMA_VERSION = "1.2.0"

@dataclass(frozen=True)
class FeatureEnvelope:
    symbol: str
    as_of: str
    calculation_timestamp: str
    available_at: str
    source: str
    schema_version: str
    features: dict
    quality: dict

    def to_dict(self):
        return asdict(self)

REQUIRED_FEATURES = {
    "momentum_1","momentum_5","volume_ratio","vwap_distance_pct",
    "intraday_range_pct","volatility_5","relative_strength",
}

def _iso_now():
    return datetime.now().astimezone().isoformat()

def validate_feature_payload(features):
    features = dict(features or {})
    missing = sorted(REQUIRED_FEATURES - set(features.keys()))
    nulls = sorted(k for k in REQUIRED_FEATURES if features.get(k) is None)
    names = validate_feature_names(features)
    versions = {
        name: FEATURE_REGISTRY[name].version
        for name in sorted(set(features) & set(FEATURE_REGISTRY))
    }
    ids = {
        name: FEATURE_REGISTRY[name].feature_id
        for name in sorted(set(features) & set(FEATURE_REGISTRY))
    }
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "feature_registry_version": FEATURE_REGISTRY_VERSION,
        "feature_versions": versions,
        "feature_ids": ids,
        "valid_schema": len(missing) == 0 and names["all_names_registered"],
        "missing_fields": missing,
        "unregistered_features": names["unregistered"],
        "null_required_fields": nulls,
        "completeness": round(
            (len(REQUIRED_FEATURES) - len(nulls) - len(missing))
            / max(len(REQUIRED_FEATURES), 1),
            4,
        ),
    }

def build_feature_envelope(
    symbol,
    features,
    *,
    as_of=None,
    calculation_timestamp=None,
    available_at=None,
    source="unknown",
):
    as_of = as_of or _iso_now()
    calculation_timestamp = calculation_timestamp or as_of
    available_at = available_at or calculation_timestamp
    quality = validate_feature_payload(features)
    return FeatureEnvelope(
        symbol=str(symbol),
        as_of=as_of,
        calculation_timestamp=calculation_timestamp,
        available_at=available_at,
        source=source,
        schema_version=FEATURE_SCHEMA_VERSION,
        features=dict(features or {}),
        quality=quality,
    )

def append_feature_snapshot(path, envelope):
    item = envelope.to_dict() if isinstance(envelope, FeatureEnvelope) else dict(envelope)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item
