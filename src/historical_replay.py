from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, time
from statistics import mean, median

from .feature_engine import build_features

REPLAY_SCHEMA_VERSION = "1.0"
FORMAL_SCAN_TIMES = [
    time(9, 5),
    time(9, 15),
    time(9, 30),
    time(9, 50),
    time(10, 15),
]


@dataclass(frozen=True)
class ReplayPolicy:
    horizon_bars: int = 12
    max_price: float = 100.0
    min_history_bars: int = 6
    round_trip_cost_pct: float = 0.45
    min_stop_pct: float = 0.8
    volatility_stop_multiplier: float = 2.0

    def to_dict(self):
        return asdict(self)


def _parse_dt(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _normalize_bars(data):
    out = []
    for raw in data or []:
        try:
            dt = _parse_dt(raw.get("date") or raw.get("datetime") or raw.get("timestamp"))
            close = float(raw["close"])
            high = float(raw["high"])
            low = float(raw["low"])
            volume = float(raw.get("volume") or 0.0)
            avg = raw.get("average")
            avg = float(avg) if avg not in (None, "") else None
        except Exception:
            continue
        out.append({
            "date": dt.isoformat(),
            "_dt": dt,
            "open": float(raw.get("open") or close),
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "average": avg,
        })
    out.sort(key=lambda x: x["_dt"])
    return out


def _group_days(bars):
    days = defaultdict(list)
    for bar in bars:
        days[bar["_dt"].date()].append(bar)
    return days


def _previous_close_map(days):
    keys = sorted(days)
    result = {}
    for i, d in enumerate(keys):
        if i == 0 or not days[keys[i - 1]]:
            result[d] = None
        else:
            result[d] = float(days[keys[i - 1]][-1]["close"])
    return result


def _stop_distance_pct(features, policy):
    vol = features.get("volatility_5")
    try:
        vol = abs(float(vol))
    except Exception:
        vol = 0.0
    return max(policy.min_stop_pct, vol * policy.volatility_stop_multiplier)


def _future_label(day_bars, index, entry, stop_pct, horizon_bars, cost_pct):
    future = day_bars[index + 1:index + 1 + horizon_bars]
    if not future or entry <= 0 or stop_pct <= 0:
        return None

    exit_price = float(future[-1]["close"])
    high = max(float(x["high"]) for x in future)
    low = min(float(x["low"]) for x in future)

    gross_ret_pct = (exit_price / entry - 1.0) * 100.0
    net_ret_pct = gross_ret_pct - float(cost_pct)
    mfe_pct = (high / entry - 1.0) * 100.0
    mae_pct = (low / entry - 1.0) * 100.0
    r_multiple = net_ret_pct / stop_pct

    return {
        "status": "COMPLETE",
        "horizon_bars": len(future),
        "gross_ret_pct": round(gross_ret_pct, 6),
        "net_ret_pct": round(net_ret_pct, 6),
        "mfe_pct": round(mfe_pct, 6),
        "mae_pct": round(mae_pct, 6),
        "stop_distance_pct": round(stop_pct, 6),
        "r_multiple": round(r_multiple, 6),
        "hit_target": bool(mfe_pct >= 2.0 * stop_pct),
        "hit_stop": bool(mae_pct <= -stop_pct),
        "label_method": "HORIZON_NET_RETURN_NORMALIZED_BY_POINT_IN_TIME_STOP",
    }


def build_symbol_snapshots(obj, policy=None, scan_times=None):
    policy = policy or ReplayPolicy()
    scan_times = list(scan_times or FORMAL_SCAN_TIMES)
    symbol = str(obj.get("symbol") or "")
    exchange = obj.get("exchange")
    bars = _normalize_bars(obj.get("data") or [])
    days = _group_days(bars)
    previous = _previous_close_map(days)
    snapshots = []

    for day in sorted(days):
        day_bars = days[day]
        pc = previous.get(day)
        if pc in (None, 0):
            continue

        for scan_time in scan_times:
            observed = [x for x in day_bars if x["_dt"].time() <= scan_time]
            if len(observed) < policy.min_history_bars:
                continue

            current = observed[-1]
            entry = float(current["close"])
            if entry <= 0 or entry > policy.max_price:
                continue

            high_so_far = max(float(x["high"]) for x in observed)
            low_so_far = min(float(x["low"]) for x in observed)
            avg_price = current.get("average")
            if avg_price is None:
                total_vol = sum(float(x.get("volume") or 0.0) for x in observed)
                if total_vol > 0:
                    avg_price = sum(
                        float(x["close"]) * float(x.get("volume") or 0.0)
                        for x in observed
                    ) / total_vol

            candidate = {
                "symbol": symbol,
                "exchange": exchange,
                "last": entry,
                "fugle_close": entry,
                "fugle_high": high_so_far,
                "fugle_low": low_so_far,
                "avg_price": avg_price,
                "change_pct": (entry / float(pc) - 1.0) * 100.0,
                "volume": sum(float(x.get("volume") or 0.0) for x in observed),
                "trade_value": sum(
                    float(x["close"]) * float(x.get("volume") or 0.0)
                    for x in observed
                ),
            }

            past_bars = [
                {k: v for k, v in x.items() if not k.startswith("_")}
                for x in observed
            ]
            features = build_features(candidate, past_bars, market_return_pct=None).to_dict()
            stop_pct = _stop_distance_pct(features, policy)

            current_index = day_bars.index(current)
            outcome = _future_label(
                day_bars,
                current_index,
                entry,
                stop_pct,
                policy.horizon_bars,
                policy.round_trip_cost_pct,
            )
            if outcome is None:
                continue

            snapshots.append({
                "schema_version": REPLAY_SCHEMA_VERSION,
                "record_id": f"replay|{symbol}|{current['_dt'].isoformat()}",
                "observed_at": current["_dt"].isoformat(),
                "symbol": symbol,
                "exchange": exchange,
                "scan_time": scan_time.strftime("%H:%M"),
                "market": {
                    "last": entry,
                    "previous_close": float(pc),
                    "change_pct": candidate["change_pct"],
                    "volume": candidate["volume"],
                    "trade_value": candidate["trade_value"],
                    "high": high_so_far,
                    "low": low_so_far,
                    "avg_price": avg_price,
                },
                "features": features,
                "outcome": outcome,
                "replay": {
                    "point_in_time_only": True,
                    "formal_scan_time": True,
                    "production_eligible": False,
                },
            })
    return snapshots


def add_cross_sectional_context(rows):
    groups = defaultdict(list)
    for row in rows or []:
        groups[(str(row.get("observed_at"))[:10], row.get("scan_time"))].append(row)

    for _, group in groups.items():
        changes = [
            float(x["market"]["change_pct"])
            for x in group
            if x.get("market", {}).get("change_pct") is not None
        ]
        if not changes:
            continue

        med = median(changes)
        breadth = mean([1.0 if x > 0 else 0.0 for x in changes])
        for row in group:
            cp = row.get("market", {}).get("change_pct")
            if cp is None:
                continue
            row["features"]["relative_strength"] = float(cp) - med
            row["market_context"] = {
                "cross_section_n": len(changes),
                "median_change_pct": round(med, 6),
                "advance_ratio": round(breadth, 6),
            }
    return rows


def replay_universe(objects, policy=None, scan_times=None):
    policy = policy or ReplayPolicy()
    rows = []
    for obj in objects or []:
        rows.extend(build_symbol_snapshots(obj, policy=policy, scan_times=scan_times))
    add_cross_sectional_context(rows)
    rows.sort(key=lambda x: (x["observed_at"], x["symbol"]))
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "policy": policy.to_dict(),
        "scan_times": [x.strftime("%H:%M") for x in (scan_times or FORMAL_SCAN_TIMES)],
        "rows": rows,
        "count": len(rows),
        "production_eligible": False,
        "limitations": [
            "Historical replay is research-only and cannot create A+ by itself.",
            "Current-universe data may contain survivorship bias unless delisted names are included.",
            "Labels use future bars only after the decision timestamp; features use point-in-time bars only.",
            "R label is normalized by a deterministic point-in-time stop proxy, not a realized broker order.",
        ],
    }
