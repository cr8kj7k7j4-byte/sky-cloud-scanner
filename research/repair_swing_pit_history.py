from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path


def _contains(interval: dict, day: str) -> bool:
    start = str(interval.get("listed_from") or "")
    end = interval.get("listed_to")
    return bool(start and start <= day and (not end or day <= str(end)))


def _pit_by_symbol(pit: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in pit.get("intervals") or []:
        symbol = str(row.get("symbol") or "")
        if symbol:
            out[symbol].append(row)
    return dict(out)


def _rewrite_with_fresh_pit(payload: dict, intervals: list[dict]) -> tuple[dict, dict]:
    symbol = str(payload.get("symbol") or "")
    kept = []
    ambiguous = []
    outside = []
    for raw in payload.get("data") or []:
        day = str(raw.get("date") or raw.get("trading_date") or "")
        matches = [x for x in intervals if _contains(x, day)]
        if len(matches) != 1:
            item = {"symbol": symbol, "date": day, "matches": len(matches)}
            (ambiguous if len(matches) > 1 else outside).append(item)
            continue
        interval = matches[0]
        row = dict(raw)
        row["exchange"] = str(interval.get("exchange") or "")
        row["listed_from"] = interval.get("listed_from")
        row["listed_to"] = interval.get("listed_to")
        row["pit_reconciled"] = True
        kept.append(row)

    if ambiguous:
        raise ValueError(f"ambiguous fresh PIT mapping for {symbol}: {ambiguous[:5]}")
    if not kept:
        raise ValueError(f"no fresh-PIT bars retained for {symbol}")

    out = dict(payload)
    out["data"] = kept
    out["repair_provenance"] = {
        "method": "REUSE_RAW_HISTORY_REMAP_FRESH_PIT_V1",
        "fresh_pit_required": True,
        "outside_rows_dropped": len(outside),
    }
    body = dict(out)
    body.pop("sha256", None)
    out["sha256"] = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return out, {
        "symbol": symbol,
        "rows_kept": len(kept),
        "outside_rows_dropped": len(outside),
        "ambiguous_rows": 0,
    }


def repair(
    *,
    primary_history: str,
    fallback_history: str,
    pit_json: str,
    out_history: str,
    report_path: str,
) -> dict:
    primary = Path(primary_history)
    fallback = Path(fallback_history)
    out = Path(out_history)
    out.mkdir(parents=True, exist_ok=True)

    pit = json.loads(Path(pit_json).read_text(encoding="utf-8"))
    if pit.get("historical_universe_gate_pass") is not True:
        raise SystemExit("fresh PIT gate is not PASS")
    if (pit.get("interval_validation") or {}).get("valid") is not True:
        raise SystemExit("fresh PIT interval validation is not PASS")

    by_symbol = _pit_by_symbol(pit)

    primary_files = sorted(primary.glob("*_D.json"))
    for p in primary_files:
        shutil.copy2(p, out / p.name)

    existing = {p.stem[:-2] if p.stem.endswith("_D") else p.stem for p in out.glob("*_D.json")}
    repaired = []
    rejected = []

    for p in sorted(fallback.glob("*_D.json")):
        symbol = p.stem[:-2] if p.stem.endswith("_D") else p.stem
        if symbol in existing:
            continue
        intervals = by_symbol.get(symbol) or []
        if not intervals:
            rejected.append({"symbol": symbol, "reason": "NO_FRESH_PIT_INTERVAL"})
            continue
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            if payload.get("adjustment_capability") != "PIT_ASOF_EVENT_LEDGER":
                rejected.append({"symbol": symbol, "reason": "NOT_ADJUSTMENT_READY"})
                continue
            normalized, stats = _rewrite_with_fresh_pit(payload, intervals)
            (out / f"{symbol}_D.json").write_text(
                json.dumps(normalized, ensure_ascii=False), encoding="utf-8"
            )
            repaired.append(stats)
            existing.add(symbol)
        except Exception as exc:
            rejected.append({
                "symbol": symbol,
                "reason": f"{type(exc).__name__}:{exc}",
            })

    report = {
        "schema_version": "SWING_PIT_ARTIFACT_REPAIR_1.0",
        "primary_files": len(primary_files),
        "fallback_candidates": len(list(fallback.glob("*_D.json"))),
        "repaired_symbols": len(repaired),
        "repaired": repaired,
        "rejected_symbols": len(rejected),
        "rejected": rejected,
        "final_files": len(list(out.glob("*_D.json"))),
        "governance": {
            "new_api_calls": 0,
            "current_universe_substitution": False,
            "fresh_pit_remap_required": True,
            "ambiguous_mapping_policy": "FAIL_CLOSED",
            "missing_data_forward_fill": False,
        },
    }
    rp = Path(report_path)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary-history", required=True)
    ap.add_argument("--fallback-history", required=True)
    ap.add_argument("--pit-json", required=True)
    ap.add_argument("--out-history", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    repair(
        primary_history=args.primary_history,
        fallback_history=args.fallback_history,
        pit_json=args.pit_json,
        out_history=args.out_history,
        report_path=args.report,
    )


if __name__ == "__main__":
    main()
