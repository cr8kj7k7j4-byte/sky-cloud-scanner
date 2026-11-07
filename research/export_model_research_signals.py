"""Research observation export from actual Sky scan artifacts; never approves trades.

No synthetic price, entry, stop, target or model weights. Rejected strategy
families cannot be silently reactivated through this evidence collector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

PROXY_MODEL_IDS = frozenset({"RF_BASELINE", "XGB_BASELINE", "NN_BASELINE"})
SCHEMA = "SKY_RESEARCH_SIGNALS_V1"


def _float(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        number = float(value)
        return number if number == number and abs(number) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _identifier(*items):
    raw = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _time(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def collect(scan, *, source_run_id, source_sha, model_registry=None):
    """Build deterministic, immutable-by-ID source-linked observations.

    A model is included only when it emits an explicit prediction in the
    original scan. An absent model never becomes a synthetic observation.
    """
    observed = scan.get("run_time")
    at = _time(observed)
    provider = scan.get("market_quote_provider") or "UNKNOWN"
    eligible_market = scan.get("market_data_gate") == "PASS_FULL_MARKET_LIVE"
    universe = list(scan.get("deep") or [])
    registry = dict(model_registry or {})
    rows = []
    seen = set()
    for item in universe:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "")
        ml = item.get("ml") or {}
        predictions = ml.get("models") or []
        for pred in predictions:
            if not isinstance(pred, dict):
                continue
            model_id = str(pred.get("model") or "")
            version = str(registry.get(model_id) or "UNREGISTERED")
            if not model_id or model_id not in PROXY_MODEL_IDS:
                # Explicit adapters/versions are needed for additional models.
                continue
            key = (model_id, version, symbol)
            if key in seen:
                continue
            seen.add(key)
            raw_price = _float(item.get("last"))
            expected = _float(pred.get("expected_return_pct"))
            source_date = str(item.get("quote_date") or "")
            valid_price = bool(
                eligible_market and at and raw_price and raw_price > 0
                and source_date in {at.date().isoformat(), at.strftime("%Y%m%d")}
                and item.get("quote_source") == "Fugle bulk snapshot"
            )
            # A scanner may use verified MIS fallback; retain provenance but
            # never mislabel it as Fugle-first verified research.
            direction = ("偏多" if expected > 0 else "偏空" if expected < 0 else "中性") if (
                expected is not None and valid_price
            ) else "待確認"
            record_id = _identifier(source_run_id, source_sha, observed, model_id, version, symbol)
            rows.append({
                "record_id": record_id,
                "schema": SCHEMA,
                "source_run_id": str(source_run_id),
                "source_sha": str(source_sha),
                "observed_at": observed,
                "model_id": model_id,
                "model_version": version,
                "model_type": "UNTRAINED_DETERMINISTIC_PROXY",
                "model_validation_status": "RESEARCH_ONLY_UNVALIDATED",
                "symbol": symbol,
                "name": item.get("name"),
                "market": item.get("exchange"),
                "quote_source": item.get("quote_source") or provider,
                "quote_date": source_date or None,
                "quote_time": item.get("quote_time"),
                "reference_executed_price": raw_price if valid_price else None,
                "expected_return_pct_proxy": expected if valid_price else None,
                "direction": direction,
                "entry_trigger": None,
                "max_acceptable_price": None,
                "stop": None,
                "target_1": None,
                "target_2": None,
                "net_rr": None,
                "entry_reason": "NO_FROZEN_MODEL_SPECIFIC_EXECUTION_RULE",
                "status": "RESEARCH_OBSERVATION" if valid_price else "INSUFFICIENT_EXECUTION_EVIDENCE",
                "market_data_gate": scan.get("market_data_gate"),
                "research_only": True,
                "production_eligible": False,
                "execution_authorized": False,
                "actual_fill": False,
                "outcome": {"status": "PENDING_FUTURE_MARKET_DATA"},
            })
    report = {
        "schema": SCHEMA,
        "source_run_id": str(source_run_id),
        "source_sha": str(source_sha),
        "scan_time": observed,
        "source_quote_provider": provider,
        "market_data_gate": scan.get("market_data_gate"),
        "status": ("RECORDED_RESEARCH_OBSERVATIONS" if rows
                   else "NO_VERIFIABLE_MODEL_OBSERVATIONS"),
        "record_count": len(rows),
        "observed_model_ids": sorted({r["model_id"] for r in rows}),
        "note": ("Only explicit RF/XGB/NN deterministic proxy outputs present in scan are exported. "
                 "Do not claim six trained models, live trades, executable prices or alpha."),
        "records": rows,
        "production_eligible": False,
        "live_order_enabled": False,
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scan", required=True)
    p.add_argument("--source-run-id", required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--out", default="output/research_signals/latest.json")
    args = p.parse_args()
    source = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    report = collect(source, source_run_id=args.source_run_id,
                     source_sha=args.source_sha)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "records"},
                     ensure_ascii=False))
    # A valid empty report is still produced for later audit.
    if not report["records"]:
        print("No research signals; data/model evidence insufficient.")


if __name__ == "__main__":
    main()
