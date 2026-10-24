from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
FEATURE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class FeatureEnvelope:
    schema_version: str
    symbol: str | None
    exchange: str | None
    observed_at: str
    source: str | None
    features: dict

    def to_dict(self):
        return asdict(self)


def _time_bucket(observed_at):
    hhmm = observed_at.hour * 60 + observed_at.minute
    buckets = [
        (9 * 60 + 5, "09:05"),
        (9 * 60 + 15, "09:15"),
        (9 * 60 + 30, "09:30"),
        (9 * 60 + 50, "09:50"),
        (10 * 60 + 15, "10:15"),
    ]
    return min(buckets, key=lambda x: abs(hhmm - x[0]))[1]


def wrap_features(candidate, features, observed_at=None):
    candidate = candidate or {}
    observed_at = observed_at or datetime.now(TZ)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=TZ)
    else:
        observed_at = observed_at.astimezone(TZ)

    payload = dict(features or {})
    payload["scan_time_bucket"] = _time_bucket(observed_at)
    payload["price"] = candidate.get("last", candidate.get("fugle_close"))
    payload["change_pct"] = candidate.get("change_pct")
    payload["trade_value"] = candidate.get("trade_value")
    payload["bid"] = candidate.get("bid")
    payload["ask"] = candidate.get("ask")

    bid, ask = candidate.get("bid"), candidate.get("ask")
    spread_pct = None
    try:
        mid = (float(bid) + float(ask)) / 2.0
        if mid > 0:
            spread_pct = (float(ask) - float(bid)) / mid * 100.0
    except Exception:
        pass
    payload["spread_pct"] = spread_pct

    return FeatureEnvelope(
        schema_version=FEATURE_SCHEMA_VERSION,
        symbol=candidate.get("symbol"),
        exchange=candidate.get("exchange"),
        observed_at=observed_at.isoformat(),
        source=candidate.get("quote_source"),
        features=payload,
    )
