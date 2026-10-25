from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json

from .feature_registry import (
    FEATURE_REGISTRY,
    FEATURE_REGISTRY_VERSION,
    validate_feature_names,
)

FEATURE_SCHEMA_VERSION = "1.2.0"

@dataclass(frozen=True)
class FeatureEnvelope:
    symbol: str
    as_of: str
    calculation_timestamp: str
    available_at: str
    ingestion_timestamp: str
    source: str
    schema_version: str
    features: dict
    quality: dict
    lineage: dict

    def to_dict(self):
        return asdict(self)

REQUIRED_FEATURES = {
    "momentum_1",
    "momentum_5",
    "volume_ratio",
    "vwap_distance_pct",
    "intraday_range_pct",
    "volatility_5",
    "relative_strength",
}

def _parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def validate_feature_payload(features):
    features = dict(features or {})
    missing = sorted(REQUIRED_FEATURES - set(features.keys()))
    nulls = sorted(k for k in REQUIRED_FEATURES if features.get(k) is None)
    names = validate_feature_names(features)
    versions = {
        name: FEATURE_REGISTRY[name].version
        for name in sorted(set(features) & set(FEATURE_REGISTRY))
    }
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "feature_registry_version": FEATURE_REGISTRY_VERSION,
        "feature_versions": versions,
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
    ingestion_timestamp=None,
    source="unknown",
):
    now = datetime.now().astimezone().isoformat()
    as_of = as_of or now
    calculation_timestamp = calculation_timestamp or now
    available_at = available_at or as_of
    ingestion_timestamp = ingestion_timestamp or now

    quality = validate_feature_payload(features)
    available_dt = _parse_ts(available_at)
    calc_dt = _parse_ts(calculation_timestamp)
    as_of_dt = _parse_ts(as_of)
    causality_errors = []
    if not all((available_dt, calc_dt, as_of_dt)):
        causality_errors.append("invalid_timestamp")
    else:
        if available_dt > calc_dt:
            causality_errors.append("available_after_calculation")
        if available_dt > as_of_dt:
            causality_errors.append("available_after_as_of")
    quality["timestamp_causality_valid"] = not causality_errors
    quality["timestamp_causality_errors"] = causality_errors
    quality["valid_schema"] = quality["valid_schema"] and not causality_errors

    lineage = {
        name: {
            "version": FEATURE_REGISTRY[name].version,
            "source": FEATURE_REGISTRY[name].source,
            "formula": FEATURE_REGISTRY[name].formula,
            "lineage": FEATURE_REGISTRY[name].lineage,
            "freshness_sla": FEATURE_REGISTRY[name].freshness_sla,
            "data_quality_rule": FEATURE_REGISTRY[name].data_quality_rule,
            "deprecation_status": FEATURE_REGISTRY[name].deprecation_status,
        }
        for name in sorted(set(features or {}) & set(FEATURE_REGISTRY))
    }

    return FeatureEnvelope(
        symbol=str(symbol),
        as_of=as_of,
        calculation_timestamp=calculation_timestamp,
        available_at=available_at,
        ingestion_timestamp=ingestion_timestamp,
        source=source,
        schema_version=FEATURE_SCHEMA_VERSION,
        features=dict(features or {}),
        quality=quality,
        lineage=lineage,
    )

def append_feature_snapshot(path, envelope):
    item = envelope.to_dict() if isinstance(envelope, FeatureEnvelope) else dict(envelope)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item
