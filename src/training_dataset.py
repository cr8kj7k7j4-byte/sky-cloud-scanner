from dataclasses import dataclass, asdict
from math import isnan

DATASET_SCHEMA_VERSION = "1.0"

DEFAULT_FEATURE_KEYS = [
    "momentum_1",
    "momentum_5",
    "volume_ratio",
    "vwap_distance_pct",
    "intraday_range_pct",
    "volatility_5",
    "relative_strength",
    "change_pct",
    "trade_value",
    "spread_pct",
]

DEFAULT_TARGETS = [
    "r_multiple",
    "mfe_pct",
    "mae_pct",
    "hit_target",
    "hit_stop",
]


@dataclass(frozen=True)
class TrainingRow:
    record_id: str
    observed_at: str
    symbol: str
    features: dict
    targets: dict

    def to_dict(self):
        return asdict(self)


def _unwrap_features(record):
    f = dict(record.get("features") or {})
    if "features" in f and isinstance(f["features"], dict):
        return dict(f["features"])
    return f


def _finite_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        x = float(value)
        return None if isnan(x) else x
    except Exception:
        return None


def build_training_row(record, feature_keys=None, require_complete_outcome=True):
    record = record or {}
    outcome = dict(record.get("outcome") or {})
    if require_complete_outcome and outcome.get("status") != "COMPLETE":
        return None

    raw_features = _unwrap_features(record)
    keys = list(feature_keys or DEFAULT_FEATURE_KEYS)
    features = {}
    for key in keys:
        value = raw_features.get(key)
        if key == "trade_value":
            features[key] = _finite_number(value)
        else:
            features[key] = _finite_number(value)

    targets = {
        "r_multiple": _finite_number(outcome.get("r_multiple")),
        "mfe_pct": _finite_number(outcome.get("mfe_pct")),
        "mae_pct": _finite_number(outcome.get("mae_pct")),
        "hit_target": 1.0 if outcome.get("hit_target") is True else 0.0 if outcome.get("hit_target") is False else None,
        "hit_stop": 1.0 if outcome.get("hit_stop") is True else 0.0 if outcome.get("hit_stop") is False else None,
    }

    if all(v is None for v in features.values()):
        return None
    if targets["r_multiple"] is None:
        return None

    return TrainingRow(
        record_id=str(record.get("record_id") or ""),
        observed_at=str(record.get("observed_at") or ""),
        symbol=str(record.get("symbol") or ""),
        features=features,
        targets=targets,
    )


def build_training_dataset(records, feature_keys=None):
    rows = []
    rejected = 0
    for record in records or []:
        row = build_training_row(record, feature_keys=feature_keys)
        if row is None:
            rejected += 1
        else:
            rows.append(row.to_dict())
    rows.sort(key=lambda x: x["observed_at"])
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "feature_keys": list(feature_keys or DEFAULT_FEATURE_KEYS),
        "target_keys": list(DEFAULT_TARGETS),
        "rows": rows,
        "eligible_count": len(rows),
        "rejected_count": rejected,
    }
