"""Fail-closed horizon-specific label construction from supplied historical bars.

Offline research only. Inputs must be verified separately as actual provider records.
This does NOT certify live Fugle access, unbiased universe, executions, or labels.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
import math

from research.three_model_research_signals import parse_timestamp, verify_bars

FEATURES = ("ret_1", "ret_3", "ret_5", "vol_5", "vol_20", "volume_ratio_5", "range_pct")


def _features(bars, index):
    """Only bar observations up to and including the signal cutoff."""
    if index < 20:
        return None
    closes = [float(x["close"]) for x in bars[index-20:index+1]]
    volumes = [float(x["volume"]) for x in bars[index-20:index+1]]
    if min(closes) <= 0:
        return None
    returns = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
    def std(items):
        avg = sum(items)/len(items)
        return (sum((x-avg)**2 for x in items)/len(items))**0.5
    prior_avg = sum(volumes[-6:-1])/5
    if prior_avg <= 0:
        return None
    b = bars[index]
    return {
        "ret_1": (closes[-1]/closes[-2]-1)*100,
        "ret_3": (closes[-1]/closes[-4]-1)*100,
        "ret_5": (closes[-1]/closes[-6]-1)*100,
        "vol_5": std(returns[-5:])*100,
        "vol_20": std(returns[-20:])*100,
        "volume_ratio_5": volumes[-1]/prior_avg,
        "range_pct": (float(b["high"])-float(b["low"]))/float(b["close"])*100,
    }


def _time(bar):
    timestamp = parse_timestamp(bar["timestamp"])
    if timestamp.utcoffset().total_seconds() != 8*3600:
        raise ValueError("bar_timestamp_not_taipei")
    return timestamp


def build_rows(payload, *, horizon):
    """Construct labels without fabricating trading sessions or market provenance.

    next_day: features at session D 13:30, label next supplied trading day's
              executable OPEN to CLOSE; the label's first execution is D+1 open.
    intraday: 09:30 5m BAR_START becomes known at 09:35; features at
              09:35; proxy entry 09:40 bar OPEN to 13:20 bar CLOSE
              (bar ends at 13:25). Avoid same timestamp execution claims.
    """
    if horizon not in ("intraday", "next_day"):
        raise ValueError("invalid_horizon")
    if not isinstance(payload, dict) or payload.get("source") != "FUGLE":
        raise ValueError("source_claim_required_not_verified")
    if payload.get("bar_timestamp_semantics") != "BAR_START":
        raise ValueError("bar_start_timestamp_semantics_unverified")
    as_of = parse_timestamp(payload.get("as_of"))
    symbols = payload.get("symbols")
    if not isinstance(symbols, dict) or not symbols:
        raise ValueError("missing_symbols")
    rows = []
    for symbol, data in sorted(symbols.items()):
        if not isinstance(symbol, str) or not symbol.isdigit() or len(symbol) not in (4, 5):
            raise ValueError("invalid_symbol")
        if not isinstance(data, dict):
            raise ValueError("invalid_symbol_payload")
        kind = "bars_daily" if horizon == "next_day" else "bars_5m"
        raw = data.get(kind)
        # Validate the full sequence. Empty or partial series cannot be inferred.
        verify_bars(raw, as_of, 22)
        bars = list(raw)
        times = [_time(b) for b in bars]
        if horizon == "next_day":
            if any(t.time() != time(13, 30) for t in times):
                raise ValueError("daily_bar_close_time_not_verified")
            for i in range(20, len(bars)-1):
                now, later = times[i], times[i+1]
                if now.date() >= later.date():
                    raise ValueError("daily_sessions_not_increasing")
                features = _features(bars, i)
                if features is None:
                    continue
                # Signal at prior session close; D+1 open not known at signal.
                entry = float(bars[i+1]["open"])
                exit_price = float(bars[i+1]["close"])
                record = {"symbol": symbol, "date": now.isoformat(),
                          "feature_available_at": now.isoformat(),
                          "label_start_at": later.replace(hour=9, minute=0).isoformat(),
                          "label_end_at": later.isoformat(),
                          "target_return_pct": (exit_price/entry-1)*100,
                          **features}
                rows.append(record)
        else:
            # Clock definitions are contract choices and require W0 review.
            if any(t.minute % 5 != 0 or not (time(9,0) <= t.time() <= time(13,25)) for t in times):
                raise ValueError("unexpected_5m_bar_timestamp")
            by_day = {}
            for i, stamp in enumerate(times):
                day_bars = by_day.setdefault(stamp.date(), {})
                if stamp.time() in day_bars:
                    raise ValueError("duplicate_5m_session_time")
                day_bars[stamp.time()] = i
            for day, positions in sorted(by_day.items()):
                if not all(x in positions for x in (time(9,30), time(9,35), time(9,40), time(13,20))):
                    continue
                i, j, k = [positions[x] for x in (time(9,30),time(9,40),time(13,20))]
                if not i < j < k or j != i+2:
                    continue
                # Reject missing, irregular or incomplete intraday bars.
                # A future terminal close cannot substitute for a continuous path.
                expected_bars = int((times[k] - times[i]).total_seconds() // 300)
                if k - i != expected_bars:
                    continue
                if any((times[n+1]-times[n]).total_seconds() != 300
                       for n in range(i,k)):
                    continue
                features = _features(bars,i)
                if features is None:
                    continue
                entry, exit_price = float(bars[j]["open"]), float(bars[k]["close"])
                record = {"symbol":symbol,"date":(times[i]+timedelta(minutes=5)).isoformat(),
                          "feature_available_at":(times[i]+timedelta(minutes=5)).isoformat(),
                          "label_start_at":times[j].isoformat(),
                          "label_end_at":(times[k]+timedelta(minutes=5)).isoformat(),
                          "target_return_pct":(exit_price/entry-1)*100,**features}
                rows.append(record)
    # No model credentials, no adjusted prices, no claim of actual fills.
    return rows


def build_audit(payload, horizon):
    rows = build_rows(payload, horizon=horizon)
    return {"schema": "sky-direction-label-research-v1", "horizon": horizon,
            "features": list(FEATURES), "rows": rows,
            "source_claim": "FUGLE", "provider_response_verified": False,
            "backtest_label_only": True, "executed_trades_verified": False,
            "production_eligible": False, "probabilities_verified": False}


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--horizon", required=True, choices=["intraday","next_day"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    incoming = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = build_audit(incoming, args.horizon)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status":"RESEARCH_ONLY","row_count":len(result["rows"]),
                      "source_verified":False,"production_eligible":False},ensure_ascii=False))


if __name__ == "__main__":
    main()
