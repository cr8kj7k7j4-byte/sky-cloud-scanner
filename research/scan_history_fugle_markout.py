"""Manual paid-Fugle historical research markout; no deployment or order actions."""
import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from research.three_model_fugle_pipeline import read_fugle
from research.scan_history_markout import research_markout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="1101,8088")
    parser.add_argument("--end", required=True)
    parser.add_argument("--days", type=int, default=120)
    args = parser.parse_args()
    symbols = [x.strip() for x in args.symbols.split(",")]
    if not symbols or len(symbols) > 5 or any(not x.isdigit() or len(x) not in (4, 5) for x in symbols):
        raise ValueError("invalid_symbols")
    if not 40 <= args.days <= 300:
        raise ValueError("invalid_days")
    end = date.fromisoformat(args.end)
    taipei_today = datetime.now(timezone(timedelta(hours=8))).date()
    if end >= taipei_today:
        raise ValueError("end_must_be_completed_past_date")
    start = end - timedelta(days=args.days)
    key = os.getenv("FUGLE_API_KEY", "")
    if not key:
        raise ValueError("missing_FUGLE_API_KEY")
    rows = []
    for symbol in symbols:
        for model, timeframe, horizon in (("bidirectional_intraday", "5", 1),
                                          ("next_day", "D", 1),
                                          ("swing_3_20d", "D", 5)):
            try:
                bars = read_fugle(symbol, timeframe, start, end, key)
                result = research_markout(symbol, model, bars, horizon=horizon)
                rows.append({k: result.get(k) for k in
                             ("status", "symbol", "model", "observation_count",
                              "net_average_return", "positive_net_fraction", "cost_assumption",
                              "limitations", "production_signal")})
            except Exception as exc:
                # Do not emit paid OHLCV or API secrets in logs/artifacts.
                rows.append({"symbol": symbol, "model": model,
                             "status": "DATA_BLOCKED", "error_type": type(exc).__name__,
                             "production_signal": False})
    completed = sum(x["status"] in ("RESEARCH_ONLY", "NO_OBSERVATIONS") for x in rows)
    blocked = sum(x["status"] == "DATA_BLOCKED" for x in rows)
    report = {"schema": "SKY_FUGLE_MARKOUT_SANITIZED_V1", "requested_end": str(end),
              "requested_models": len(rows), "completed_models": completed,
              "blocked_models": blocked, "complete_coverage": blocked == 0,
              "source": "Fugle paid historical candles", "results": rows,
              "historical_only": True, "production_signal": False}
    Path("output").mkdir(exist_ok=True)
    Path("output/fugle_markout_sanitized.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if completed == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
