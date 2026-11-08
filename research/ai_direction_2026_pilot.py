"""Small-sample real-data historical AI probability audit; never production.

Needs FUGLE_API_KEY in secure GitHub Actions environment. No raw market data
or model weights are publicly published. This is a two-symbol *pilot*, not
whole-universe, forward or production validation.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path

TPE = timezone(timedelta(hours=8))
DEFAULT_SYMBOLS = ("1101", "8088")


def run(*, api_key, start, end, symbols=DEFAULT_SYMBOLS, reader=None):
    import pandas as pd
    from research.ai_direction_classifier import train
    from research.ai_direction_labels import build_audit, FEATURES

    if not api_key:
        raise ValueError("FUGLE_API_KEY_not_configured")
    if not isinstance(start, date) or not isinstance(end, date) or end < start:
        raise ValueError("invalid_date_window")
    if end > datetime.now(TPE).date() or (end-start).days >= 365:
        raise ValueError("unavailable_date_window")
    if not symbols or len(symbols) > 10 or len(set(symbols)) != len(symbols):
        raise ValueError("invalid_symbol_list")
    if reader is None:
        from research.three_model_fugle_pipeline import read_fugle
        reader=read_fugle
    source = {"source": "FUGLE", "as_of": datetime.now(TPE).isoformat(),
              "bar_timestamp_semantics": "BAR_START", "symbols": {}}
    source_counts = {}
    for symbol in symbols:
        if not isinstance(symbol, str) or not symbol.isdigit() or len(symbol) not in (4,5):
            raise ValueError("invalid_symbol")
        intraday = reader(symbol, "5", start, end, api_key)
        daily = reader(symbol, "D", start, end, api_key)
        source["symbols"][symbol] = {"bars_5m": intraday, "bars_daily": daily}
        source_counts[symbol] = {"bars_5m": len(intraday), "bars_daily": len(daily)}
    audits = {}
    for horizon in ("intraday", "next_day"):
        labeled = build_audit(source, horizon)
        if not labeled["rows"]:
            audits[horizon] = {"status": "INSUFFICIENT_DATA", "labeled_rows": 0}
            continue
        df = pd.DataFrame(labeled["rows"])
        for column in ("date", "feature_available_at", "label_start_at", "label_end_at"):
            df[column] = pd.to_datetime(df[column], utc=True)
        # The embargo is conservative *in addition to* actual label-end purge.
        embargo = 2 if horizon == "next_day" else 1
        try:
            report = train(df, list(FEATURES), horizon=horizon, embargo_sessions=embargo)
            audits[horizon] = {
                "status": "HISTORICAL_PILOT_ONLY", "labeled_rows": len(df),
                "unique_session_dates": int(df["date"].dt.date.nunique()),
                "symbol_count": int(df["symbol"].nunique()),
                "max_symbol_share": round(float(df["symbol"].value_counts(normalize=True).max()), 6),
                "holdout": report["splits"],
                "metrics": report["models"],
                "train_only_constant_baseline_oos": report["train_only_constant_baseline_oos"],
            }
        except (ValueError, RuntimeError) as exc:
            audits[horizon] = {"status": "INSUFFICIENT_DATA",
                               "labeled_rows": len(df),
                               "reason": type(exc).__name__}
    return {
        "schema": "sky-ai-direction-2026-fixed-cohort-historical-pilot-v1",
        "period_requested": {"start":start.isoformat(), "end":end.isoformat()},
        "source": "Fugle historical/candles",
        "historical_api_response_received": True,
        "source_counts": source_counts,
        "results": audits,
        "universe_coverage_verified": False,
        "fresh_untouched_oos": False,
        "sample_is_independent_trades": False,
        "trade_executions_verified": False,
        "market_hours_and_calendar_reconciled": False,
        "probabilities_verified_for_mobile": False,
        "production_eligible": False,
        "order_authorized": False,
        "note": "Retrospective 2026 fixed-cohort pilot; 2026 has already been researched. "
                "No fresh OOS, no calibrated live probabilities, no cost-after-execution claim."
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-01")
    ap.add_argument("--end", default="2026-11-07")
    ap.add_argument("--symbols", default="1101,8088")
    ap.add_argument("--out", default="research_output/ai_direction_2026_pilot_summary.json")
    args = ap.parse_args()
    symbols = tuple(x.strip() for x in args.symbols.split(",") if x.strip())
    result = run(api_key=os.getenv("FUGLE_API_KEY", "").strip(),
                 start=date.fromisoformat(args.start),
                 end=date.fromisoformat(args.end),symbols=symbols)
    output = Path(args.out)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"schema":result["schema"],
                      "summary_path":str(output),
                      "horizons":{k:v["status"] for k,v in result["results"].items()},
                      "production_eligible":False},ensure_ascii=False))


if __name__ == "__main__":
    main()
