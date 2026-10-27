from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.official import fetch_mis_quotes, load_official_universe

TZ = ZoneInfo("Asia/Taipei")
FRESH_START = "2026-10-27"
PRIMARY_COST = 0.0045
STRESS_COST = 0.0065


def _f(v):
    try:
        return float(v)
    except Exception:
        return None


def _mean(xs):
    return statistics.mean(xs) if xs else None


def _pstdev(xs):
    return statistics.pstdev(xs) if len(xs) >= 2 else None


def _ecdf(values, x):
    vals = [v for v in values if v is not None and math.isfinite(v)]
    if not vals or x is None or not math.isfinite(x):
        return None
    return sum(v <= x for v in vals) / len(vals)


def load_base_history(history_dir: str) -> dict[str, list[dict]]:
    bysym = {}
    for p in sorted(Path(history_dir).rglob("*_D.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        sym = str(obj.get("symbol") or p.stem.replace("_D", ""))
        rows = obj.get("data") or obj.get("rows") or obj.get("history") or []
        arr = []
        for r in rows:
            ds = str(r.get("date") or r.get("trading_date") or "")[:10]
            op, hi, lo, cl = map(_f, (r.get("open"), r.get("high"), r.get("low"), r.get("close")))
            vol = _f(r.get("volume")) or 0.0
            if ds and None not in (op, hi, lo, cl):
                arr.append({"date": ds, "open": op, "high": hi, "low": lo, "close": cl, "volume": vol})
        arr.sort(key=lambda x: x["date"])
        if arr:
            bysym[sym] = arr
    return bysym


def load_state(path: str | None) -> dict:
    if not path:
        return {"version": 1, "snapshots": {}, "signals": []}
    p = Path(path)
    if not p.exists():
        return {"version": 1, "snapshots": {}, "signals": []}
    state = json.loads(p.read_text(encoding="utf-8"))
    state.setdefault("version", 1)
    state.setdefault("snapshots", {})
    state.setdefault("signals", [])
    return state


def normalize_snapshot(rows: list[dict], date_str: str) -> dict[str, dict]:
    out = {}
    for r in rows:
        sym = str(r.get("symbol") or "")
        op, hi, lo, cl = map(_f, (r.get("open"), r.get("high"), r.get("low"), r.get("last")))
        vol = _f(r.get("volume"))
        if not sym or None in (op, hi, lo, cl, vol):
            continue
        out[sym] = {
            "date": date_str,
            "open": op,
            "high": hi,
            "low": lo,
            "close": cl,
            "volume": vol,
            "exchange": r.get("exchange"),
            "quote_time": r.get("quote_time"),
            "quote_source": r.get("quote_source"),
        }
    return out


def merge_history(base: dict[str, list[dict]], snapshots: dict[str, dict]) -> dict[str, list[dict]]:
    bysym = {s: [dict(x) for x in rows] for s, rows in base.items()}
    for ds in sorted(snapshots):
        for sym, row in snapshots[ds].items():
            arr = bysym.setdefault(sym, [])
            arr = [x for x in arr if x["date"] != ds]
            arr.append({k: row[k] for k in ("date", "open", "high", "low", "close", "volume")})
            arr.sort(key=lambda x: x["date"])
            bysym[sym] = arr
    return bysym


def _row_index(days: list[dict], date_str: str):
    for i, r in enumerate(days):
        if r["date"] == date_str:
            return i
    return None


def raw_features_for_date(bysym: dict[str, list[dict]], date_str: str) -> list[dict]:
    raw = []
    for sym, days in bysym.items():
        i = _row_index(days, date_str)
        if i is None or i < 60:
            continue
        closes = [x["close"] for x in days]
        highs = [x["high"] for x in days]
        vols = [x.get("volume", 0.0) for x in days]
        ma20 = _mean(closes[i-19:i+1])
        ma60 = _mean(closes[i-59:i+1])
        if not ma20 or not ma60 or closes[i-20] == 0 or closes[i-5] == 0 or closes[i-1] == 0:
            continue
        rets = []
        ok = True
        for j in range(i-19, i+1):
            if j <= 0 or closes[j-1] == 0:
                ok = False
                break
            rets.append(closes[j] / closes[j-1] - 1.0)
        if not ok:
            continue
        vol20 = _pstdev(rets)
        vmean = _mean(vols[i-19:i+1])
        d = days[i]
        raw.append({
            "symbol": sym,
            "date": date_str,
            "close": d["close"],
            "open": d["open"],
            "high": d["high"],
            "low": d["low"],
            "volume": d.get("volume", 0.0),
            "ma20": ma20,
            "ma60": ma60,
            "ret5": d["close"] / closes[i-5] - 1.0,
            "ret20": d["close"] / closes[i-20] - 1.0,
            "prior20_high": max(highs[i-20:i]),
            "range_pct": (d["high"] - d["low"]) / d["close"] if d["close"] else None,
            "distance_ma20": d["close"] / ma20 - 1.0,
            "gap_abs": abs(d["open"] / closes[i-1] - 1.0),
            "volume_ratio20": (d.get("volume", 0.0) / vmean) if vmean and vmean > 0 else None,
            "realized_vol20": vol20,
        })
    return raw


def cross_section(bysym: dict[str, list[dict]], date_str: str) -> dict:
    raw = raw_features_for_date(bysym, date_str)
    if len(raw) < 20:
        return {"date": date_str, "raw": [], "breadth": None, "rs": {}}
    breadth = sum(r["close"] > r["ma20"] for r in raw) / len(raw)
    vals = [r["ret20"] for r in raw]
    rs = {r["symbol"]: _ecdf(vals, r["ret20"]) for r in raw}
    for r in raw:
        r["breadth"] = breadth
        r["rs_pct"] = rs[r["symbol"]]
    return {"date": date_str, "raw": raw, "breadth": breadth, "rs": rs}


def market_dates_from_history(bysym: dict[str, list[dict]]) -> list[str]:
    c = Counter()
    for rows in bysym.values():
        c.update(x["date"] for x in rows)
    if not c:
        return []
    max_cross = max(c.values())
    threshold = max(20, int(max_cross * 0.80))
    return sorted(d for d, n in c.items() if n >= threshold)


def build_breakout_events(bysym: dict[str, list[dict]], date_str: str) -> list[dict]:
    dates = market_dates_from_history(bysym)
    if date_str not in dates:
        return []
    pos = dates.index(date_str)
    if pos < 5:
        return []
    prev5 = dates[pos-5]
    now = cross_section(bysym, date_str)
    old = cross_section(bysym, prev5)
    if now["breadth"] is None or old["breadth"] is None:
        return []
    old_rs = old["rs"]
    events = []
    for r in now["raw"]:
        sym = r["symbol"]
        rs_delta5 = None if sym not in old_rs else r["rs_pct"] - old_rs[sym]
        x = dict(r)
        x["breadth_delta5"] = now["breadth"] - old["breadth"]
        x["rs_delta5"] = rs_delta5
        if x["breadth"] < 0.50:
            continue
        if not (x["close"] > x["ma20"] > x["ma60"]):
            continue
        if x["rs_pct"] is None or x["rs_pct"] < 0.70:
            continue
        if not (x["close"] > x["prior20_high"]):
            continue
        if x["distance_ma20"] > 0.08:
            continue
        if x["range_pct"] is None or x["range_pct"] > 0.08:
            continue
        required = ["breadth","breadth_delta5","rs_pct","rs_delta5","volume_ratio20",
                    "ret5","ret20","distance_ma20","range_pct","realized_vol20","gap_abs"]
        if any(x.get(k) is None for k in required):
            continue
        events.append(x)
    return events


def score_events(events: list[dict]) -> list[dict]:
    if not events:
        return []
    pos_keys = ["breadth","breadth_delta5","rs_pct","rs_delta5","volume_ratio20","ret5","ret20"]
    inv_keys = ["distance_ma20","range_pct","realized_vol20","gap_abs"]
    values = {k: [e[k] for e in events] for k in pos_keys + inv_keys}
    scored = []
    for e in events:
        parts = []
        for k in pos_keys:
            parts.append(_ecdf(values[k], e[k]))
        for k in inv_keys:
            p = _ecdf(values[k], e[k])
            parts.append(None if p is None else 1.0 - p)
        if any(p is None for p in parts):
            continue
        x = dict(e)
        x["score"] = sum(parts) / len(parts)
        scored.append(x)
    score_vals = [x["score"] for x in scored]
    for x in scored:
        x["score_pct"] = _ecdf(score_vals, x["score"])
        x["selected"] = x["score_pct"] is not None and x["score_pct"] >= 0.90
    return scored


def add_signals(state: dict, scored: list[dict], date_str: str) -> int:
    if date_str <= FRESH_START:
        return 0
    existing = {(x["signal_date"], x["symbol"]) for x in state["signals"]}
    added = 0
    for x in scored:
        if not x.get("selected"):
            continue
        key = (date_str, x["symbol"])
        if key in existing:
            continue
        state["signals"].append({
            "strategy_id": "trend_persistence_v1_1",
            "signal_date": date_str,
            "symbol": x["symbol"],
            "score": x["score"],
            "score_pct": x["score_pct"],
            "status": "PENDING",
            "entry_date": None,
            "entry_open": None,
            "outcome_date": None,
            "exit_close": None,
            "gross_f5": None,
            "net_045": None,
            "net_065": None,
        })
        added += 1
    return added


def evaluate_matured(state: dict) -> int:
    dates = sorted(state["snapshots"])
    matured = 0
    for s in state["signals"]:
        if s.get("status") in {"EVALUATED", "ENTRY_REJECTED_PRICE"}:
            continue
        d = s["signal_date"]
        later = [x for x in dates if x > d]
        if not later:
            continue
        d1 = later[0]
        r1 = state["snapshots"].get(d1, {}).get(s["symbol"])
        if not r1:
            continue
        entry = _f(r1.get("open"))
        if entry in (None, 0):
            continue
        s["entry_date"] = d1
        s["entry_open"] = entry
        if entry >= 100:
            s["status"] = "ENTRY_REJECTED_PRICE"
            continue
        if s.get("status") == "PENDING":
            s["status"] = "ENTRY_ACCEPTED_PENDING"
        if len(later) < 5:
            continue
        d5 = later[4]
        r5 = state["snapshots"].get(d5, {}).get(s["symbol"])
        if not r5:
            s["status"] = "MATURED_INCOMPLETE"
            continue
        exit_ = _f(r5.get("close"))
        if exit_ is None:
            s["status"] = "MATURED_INCOMPLETE"
            continue
        gross = exit_ / entry - 1.0
        s.update({
            "status": "EVALUATED",
            "outcome_date": d5,
            "exit_close": exit_,
            "gross_f5": gross,
            "net_045": gross - PRIMARY_COST,
            "net_065": gross - STRESS_COST,
        })
        matured += 1
    return matured


def _pf(vals):
    gains = sum(v for v in vals if v > 0)
    losses = -sum(v for v in vals if v < 0)
    return gains / losses if losses > 0 else None


def build_dashboard(state: dict) -> dict:
    evaluated = [x for x in state["signals"] if x.get("status") == "EVALUATED"]
    dates = sorted(d for d in state["snapshots"] if d > FRESH_START)
    matured_pool = []
    all_dates = sorted(state["snapshots"])
    for x in state["signals"]:
        if x.get("status") == "ENTRY_REJECTED_PRICE":
            continue
        if len([d for d in all_dates if d > x["signal_date"]]) >= 5:
            matured_pool.append(x)
    completeness = (
        sum(x.get("status") == "EVALUATED" for x in matured_pool) / len(matured_pool)
        if matured_pool else 1.0
    )
    vals45 = [x["net_045"] for x in evaluated]
    vals65 = [x["net_065"] for x in evaluated]
    counts = Counter(x["symbol"] for x in evaluated)
    single_share = (max(counts.values()) / len(evaluated)) if evaluated and counts else 0.0

    exp45 = statistics.mean(vals45) if vals45 else None
    exp65 = statistics.mean(vals65) if vals65 else None
    pf45 = _pf(vals45) if vals45 else None

    sufficiency = (
        len(evaluated) >= 200
        and len(dates) >= 20
        and completeness >= 0.95
        and single_share <= 0.20
    )

    if not sufficiency:
        decision = "WAITING_FOR_SUFFICIENCY"
    elif exp45 is None or pf45 is None or exp65 is None:
        decision = "HOLD_INCOMPLETE_METRICS"
    elif exp45 <= 0 or pf45 <= 1 or exp65 <= 0:
        decision = "REJECT_CANDIDATE"
    else:
        decision = "HOLD_REGIME_DATA_BLOCKED"

    return {
        "strategy_id": "trend_persistence_v1_1",
        "fresh_oos_start_exclusive": FRESH_START,
        "fresh_trading_days": len(dates),
        "signal_count": len(state["signals"]),
        "entry_rejected_price_count": sum(x.get("status") == "ENTRY_REJECTED_PRICE" for x in state["signals"]),
        "evaluable_count": len(evaluated),
        "matured_pool_count": len(matured_pool),
        "outcome_completeness": completeness,
        "single_symbol_share": single_share,
        "expectancy_045": exp45,
        "pf_045": pf45,
        "expectancy_065": exp65,
        "regime_gate": "DATA_BLOCKED",
        "regime_note": "PIT-safe market benchmark not yet integrated; no proxy substitution allowed.",
        "sufficiency_pass": sufficiency,
        "decision": decision,
        "production_change": False,
    }


def render_md(d: dict) -> str:
    pct = lambda x: "N/A" if x is None else f"{x*100:.4f}%"
    pf = "N/A" if d.get("pf_045") is None else f"{d['pf_045']:.4f}"
    return "\n".join([
        "# Trend Persistence V1.1 Prospective Dashboard",
        f"- Fresh OOS start: > {FRESH_START}",
        f"- Fresh trading days: {d['fresh_trading_days']}",
        f"- Signals: {d['signal_count']}",
        f"- Evaluable: {d['evaluable_count']}",
        f"- Outcome completeness: {d['outcome_completeness']*100:.2f}%",
        f"- Single-symbol share: {d['single_symbol_share']*100:.2f}%",
        f"- 0.45% expectancy: {pct(d.get('expectancy_045'))}",
        f"- 0.45% PF: {pf}",
        f"- 0.65% expectancy: {pct(d.get('expectancy_065'))}",
        f"- Regime gate: {d['regime_gate']}",
        f"- Decision: **{d['decision']}**",
        "",
        "Production remains unchanged.",
    ])


def run(history_dir: str, previous_state: str | None, out_dir: str):
    now = datetime.now(TZ)
    if now.time() < dtime(13, 40):
        raise RuntimeError("Prospective EOD snapshot must run after 13:40 Asia/Taipei")

    universe, health = load_official_universe()
    quotes, warnings = fetch_mis_quotes(universe)
    coverage = len(quotes) / len(universe) if universe else 0.0
    if coverage < 0.80:
        raise RuntimeError(f"Whole-market operational coverage too low: {coverage:.4f}")

    date_str = now.date().isoformat()
    snapshot = normalize_snapshot(quotes, date_str)
    if len(snapshot) < int(len(universe) * 0.80):
        raise RuntimeError("Normalized EOD snapshot coverage below 80%")

    state = load_state(previous_state)
    state["snapshots"][date_str] = snapshot

    base = load_base_history(history_dir)
    bysym = merge_history(base, state["snapshots"])
    events = build_breakout_events(bysym, date_str)
    scored = score_events(events)
    added = add_signals(state, scored, date_str)
    matured = evaluate_matured(state)
    dashboard = build_dashboard(state)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    (out / "dashboard.json").write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "latest.md").write_text(render_md(dashboard), encoding="utf-8")
    run_meta = {
        "generated_at": now.isoformat(),
        "snapshot_date": date_str,
        "universe_count": len(universe),
        "quote_count": len(quotes),
        "snapshot_count": len(snapshot),
        "coverage": coverage,
        "official_universe_health": health,
        "warnings": warnings,
        "breakout_event_count": len(events),
        "scored_event_count": len(scored),
        "selected_added": added,
        "newly_matured": matured,
        "decision": dashboard["decision"],
    }
    (out / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(render_md(dashboard))
    return dashboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-dir", required=True)
    ap.add_argument("--previous-state")
    ap.add_argument("--out", default="output/trend_persistence_prospective")
    args = ap.parse_args()
    run(args.history_dir, args.previous_state, args.out)


if __name__ == "__main__":
    main()
