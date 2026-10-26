from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from research.backtest_opening_acceleration_baseline_c import (
    PRIMARY_COST,
    STRESS_COST,
    build_snapshot_db,
    enrich_rows,
    select_variant,
    metrics,
    concentration,
    subgroup,
)

SCHEMA_VERSION = "OPENING_ACCELERATION_BASELINE_D_RECLAIM_V1_0"


def minute_plus(hhmm: str, minutes: int = 1) -> str:
    dt = datetime.strptime(hhmm, "%H:%M") + timedelta(minutes=minutes)
    return dt.strftime("%H:%M")


def load_day_map(data_root: str) -> dict:
    out = {}
    for p in sorted(Path(data_root).rglob("*_opening_1m.json")):
        x = json.loads(p.read_text(encoding="utf-8"))
        symbol = str(x.get("symbol") or "")
        exchange = str(x.get("exchange") or "")
        for d in x.get("days") or []:
            day = str(d.get("date") or "")
            if day:
                out[(day, symbol)] = {
                    "exchange": exchange,
                    **d,
                }
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def apply_outcome(seed: dict, day_obj: dict, entry_hhmm: str) -> dict | None:
    o = dict((day_obj.get("outcomes") or {}).get(entry_hhmm) or {})
    if o.get("entry_status") != "ENTRY_4TICK_ZONE" or not o.get("entry"):
        return None

    d = dict(seed)
    d["baseline_c_seed_obs"] = seed["obs"]
    d["d_entry_obs"] = entry_hhmm
    d["entry"] = float(o["entry"])
    d["entry_status"] = o.get("entry_status")
    d["open_stop_triggered"] = bool(o.get("open_stop_triggered"))
    d["open_stop_time"] = o.get("open_stop_time")
    d["open_stop_fill"] = o.get("open_stop_fill")
    for k in (
        "exit_30m", "exit_60m", "stop_aware_exit_30m", "stop_aware_exit_60m",
        "session_close", "high_30m", "low_30m", "high_60m", "low_60m",
        "high_to_close", "low_to_close",
    ):
        d[k] = o.get(k)

    exit60 = d.get("stop_aware_exit_60m") or d.get("exit_60m")
    exit30 = d.get("stop_aware_exit_30m") or d.get("exit_30m")
    d["gross_30m"] = (float(exit30) / d["entry"] - 1.0) if exit30 else None
    d["gross_60m"] = (float(exit60) / d["entry"] - 1.0) if exit60 else None
    d["gross_close"] = (
        float(d["session_close"]) / d["entry"] - 1.0
        if d.get("session_close") else None
    )
    d["net_60m_045"] = (
        d["gross_60m"] - PRIMARY_COST if d["gross_60m"] is not None else None
    )
    d["net_60m_065"] = (
        d["gross_60m"] - STRESS_COST if d["gross_60m"] is not None else None
    )
    d["mfe_60m"] = (
        float(d["high_60m"]) / d["entry"] - 1.0 if d.get("high_60m") else None
    )
    d["mae_60m"] = (
        float(d["low_60m"]) / d["entry"] - 1.0 if d.get("low_60m") else None
    )
    d["mfe_to_close"] = (
        float(d["high_to_close"]) / d["entry"] - 1.0
        if d.get("high_to_close") else None
    )
    d["mae_to_close"] = (
        float(d["low_to_close"]) / d["entry"] - 1.0
        if d.get("low_to_close") else None
    )
    d["hit_plus5"] = bool(
        d["mfe_to_close"] is not None and d["mfe_to_close"] >= 0.05
    )
    d["open_stop_hit"] = bool(d.get("open_stop_triggered"))
    d["near_limit_proxy"] = bool(
        d.get("high_to_close") is not None
        and d.get("prior_close")
        and float(d["high_to_close"]) / float(d["prior_close"]) - 1.0 >= 0.095
    )
    return d


def classify_seed(seed: dict, day_obj: dict) -> tuple[str, dict]:
    bars = dict(day_obj.get("bars") or {})
    open_px = float(day_obj["session_open"])
    labels = sorted(k for k in bars if seed["obs"] <= k <= "09:14")

    pullback_label = None
    reclaim_label = None
    for label in labels:
        b = bars[label] or {}
        low = b.get("low")
        if pullback_label is None:
            if low is not None and float(low) <= open_px:
                pullback_label = label
            continue

        if label <= pullback_label:
            continue
        prev_label = minute_plus(label, -1)
        prev = bars.get(prev_label) or {}
        close = b.get("close")
        prev_high = prev.get("high")
        if (
            close is not None
            and prev_high is not None
            and float(close) > open_px
            and float(close) > float(prev_high)
        ):
            reclaim_label = label
            break

    meta = {
        "pullback_obs": pullback_label,
        "reclaim_obs": reclaim_label,
        "d_entry_obs": minute_plus(reclaim_label, 1) if reclaim_label else None,
    }

    if pullback_label is None:
        return "NO_PULLBACK_BY_ENTRY_WINDOW", meta
    if reclaim_label is None:
        return "PULLBACK_NO_RECLAIM", meta

    entry_hhmm = meta["d_entry_obs"]
    if entry_hhmm > "09:15":
        return "RECLAIM_TOO_LATE", meta

    o = dict((day_obj.get("outcomes") or {}).get(entry_hhmm) or {})
    if o.get("entry_status") == "MISSED_4TICK_NO_CHASE":
        return "RECLAIM_MISSED_4TICK_NO_CHASE", meta
    if o.get("entry_status") != "ENTRY_4TICK_ZONE" or not o.get("entry"):
        return "RECLAIM_MISSED_4TICK_NO_CHASE", meta
    return "RECLAIM_ENTRY_ELIGIBLE", meta


def taxonomy_summary(rows: list[dict]) -> dict:
    g = defaultdict(list)
    for r in rows:
        g[r["d_taxonomy"]].append(r)
    out = {}
    total = len(rows)
    for k, arr in sorted(g.items()):
        out[k] = {
            "n": len(arr),
            "share": len(arr) / total if total else 0.0,
            "baseline_c_open_stop_rate": (
                sum(bool(x.get("c_open_stop_hit")) for x in arr) / len(arr)
                if arr else 0.0
            ),
            "baseline_c_hit_plus5_rate": (
                sum(bool(x.get("c_hit_plus5")) for x in arr) / len(arr)
                if arr else 0.0
            ),
            "baseline_c_near_limit_proxy_rate": (
                sum(bool(x.get("c_near_limit_proxy")) for x in arr) / len(arr)
                if arr else 0.0
            ),
        }
    return out


def adjudicate(primary: dict, half: dict, conc: dict) -> str:
    if primary.get("n", 0) < 200:
        return "HOLD_INSUFFICIENT_SAMPLE"
    if primary.get("expectancy") is None or primary["expectancy"] <= 0:
        return "REJECT_AFTER_COST_EXPECTANCY"
    if primary.get("pf") is None or primary["pf"] <= 1:
        return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0) > 0.20:
        return "HOLD_CONCENTRATION_FAIL"
    h1 = half.get("2026-H1", {})
    h2 = half.get("2026-H2", {})
    if min(h1.get("n", 0), h2.get("n", 0)) < 50:
        return "HOLD_HALF_SAMPLE"
    if (
        h1.get("expectancy") is None or h2.get("expectancy") is None
        or (h1["expectancy"] > 0) != (h2["expectancy"] > 0)
    ):
        return "HOLD_HALF_INSTABILITY"
    return "PROMOTE_CANDIDATE_TO_W4"


def run(data_root: str, out_dir: str, source_run_id: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    db = out / "baseline_d_seed.sqlite"
    if db.exists():
        db.unlink()
    build = build_snapshot_db(data_root, str(db))
    conn = sqlite3.connect(db)
    seed_rows = enrich_rows(conn)
    conn.close()
    seeds = select_variant(seed_rows)

    day_map = load_day_map(data_root)
    taxonomy_rows = []
    d_trades = []

    for seed in seeds:
        day_obj = day_map.get((seed["session_date"], seed["symbol"]))
        if not day_obj:
            continue

        cls, meta = classify_seed(seed, day_obj)
        tax = {
            "session_date": seed["session_date"],
            "symbol": seed["symbol"],
            "exchange": seed.get("exchange"),
            "baseline_c_seed_obs": seed["obs"],
            "d_taxonomy": cls,
            **meta,
            "c_open_stop_hit": bool(seed.get("open_stop_hit")),
            "c_hit_plus5": bool(seed.get("hit_plus5")),
            "c_near_limit_proxy": bool(seed.get("near_limit_proxy")),
            "c_net_60m_045": seed.get("net_60m_045"),
        }
        taxonomy_rows.append(tax)

        if cls != "RECLAIM_ENTRY_ELIGIBLE":
            continue
        d = apply_outcome(seed, day_obj, meta["d_entry_obs"])
        if d is None:
            continue
        d["pullback_obs"] = meta["pullback_obs"]
        d["reclaim_obs"] = meta["reclaim_obs"]
        d["d_taxonomy"] = cls
        d_trades.append(d)

    write_csv(out / "baseline_d_failure_taxonomy.csv", taxonomy_rows)
    write_csv(out / "opening_acceleration_baseline_d_trades.csv", d_trades)

    gross = metrics(d_trades, "gross_60m")
    p045 = metrics(d_trades, "net_60m_045")
    p065 = metrics(d_trades, "net_60m_065")
    half = subgroup(d_trades, "half", "net_60m_045")
    minute = subgroup(d_trades, "d_entry_obs", "net_60m_045")
    conc = concentration(d_trades)
    taxonomy = taxonomy_summary(taxonomy_rows)

    c_stop_n = sum(bool(x.get("c_open_stop_hit")) for x in taxonomy_rows)
    c_stop_excluded_n = sum(
        bool(x.get("c_open_stop_hit")) and x["d_taxonomy"] != "RECLAIM_ENTRY_ELIGIBLE"
        for x in taxonomy_rows
    )
    c_plus5_n = sum(bool(x.get("c_hit_plus5")) for x in taxonomy_rows)
    c_plus5_retained_n = sum(
        bool(x.get("c_hit_plus5")) and x["d_taxonomy"] == "RECLAIM_ENTRY_ELIGIBLE"
        for x in taxonomy_rows
    )

    decision = adjudicate(p045, half, conc)
    report = {
        "schema_version": SCHEMA_VERSION,
        "preregistered_spec": "research/w5/OPENING_ACCELERATION_BASELINE_D_RECLAIM_PREREGISTRATION_20261026.md",
        "source": {
            "baseline_c_source_run_id": source_run_id,
            "historical_window": "2026-01-01/2026-10-22",
            "fresh_oos": False,
        },
        "build": build,
        "seed_population": len(seeds),
        "failure_taxonomy": taxonomy,
        "false_start_filter": {
            "baseline_c_open_stop_count": c_stop_n,
            "baseline_c_open_stop_excluded_before_d_entry": c_stop_excluded_n,
            "open_stop_exclusion_rate": c_stop_excluded_n / c_stop_n if c_stop_n else None,
            "baseline_c_plus5_count": c_plus5_n,
            "baseline_c_plus5_retained_by_d": c_plus5_retained_n,
            "plus5_retention_rate": c_plus5_retained_n / c_plus5_n if c_plus5_n else None,
        },
        "baseline_d": {
            "selected": len(d_trades),
            "selection_rate_vs_c": len(d_trades) / len(seeds) if seeds else 0.0,
            "gross_60m": gross,
            "cost_045": p045,
            "cost_065": p065,
            "half_045": half,
            "entry_minute_045": minute,
            "concentration": conc,
        },
        "decision": decision,
        "governance": {
            "production_change": False,
            "baseline_c_retuned": False,
            "fresh_oos_claim": False,
            "next_if_survives": "W4_SHADOW_PAPER_ONLY",
        },
    }

    (out / "opening_acceleration_baseline_d_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Opening Acceleration Baseline D — False-Start Reclaim",
        "",
        f"- Decision: **{decision}**",
        f"- C seed population: {len(seeds):,}",
        f"- D entries: {len(d_trades):,}",
        f"- D selection rate vs C: {report['baseline_d']['selection_rate_vs_c']:.2%}",
        f"- C open-stop exclusion before D entry: {report['false_start_filter']['open_stop_exclusion_rate']}",
        f"- C +5% retention by D: {report['false_start_filter']['plus5_retention_rate']}",
        f"- D gross 60m expectancy: {gross.get('expectancy')}",
        f"- D 0.45% expectancy: {p045.get('expectancy')}",
        f"- D 0.45% PF: {p045.get('pf')}",
        f"- D 0.65% expectancy: {p065.get('expectancy')}",
        f"- D 0.65% PF: {p065.get('pf')}",
        "",
        "## Failure taxonomy",
        "",
        json.dumps(taxonomy, ensure_ascii=False, indent=2),
        "",
        "## Half-year 0.45%",
        "",
        json.dumps(half, ensure_ascii=False, indent=2),
        "",
        "2026 is structural research data, not fresh OOS. No Production change.",
    ]
    (out / "opening_acceleration_baseline_d_report.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out-dir", default="research_output/opening_acceleration_baseline_d")
    ap.add_argument("--source-run-id", default="40267006806")
    args = ap.parse_args()
    print(json.dumps(run(args.data_root, args.out_dir, args.source_run_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
