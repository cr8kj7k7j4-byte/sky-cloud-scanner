from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCAN_TIMES = ["09:05", "09:15", "09:30", "09:50", "10:15"]
TRADE_TIMES = ["09:15", "09:30", "09:50", "10:15"]
PREV_SCAN = {"09:15":"09:05", "09:30":"09:15", "09:50":"09:30", "10:15":"09:50"}
ELAPSED_MIN = {"09:15":10.0, "09:30":15.0, "09:50":20.0, "10:15":25.0}
PRIMARY_COST = 0.0045
STRESS_COST = 0.0065
PRICE_CAP = 100.0
DAY_RETURN_CAP = 0.099
TAIPEI = timezone(timedelta(hours=8))
SCHEMA_VERSION = "W2_TOP100_VELOCITY_BASELINE_A_V1_0"


def parse_ts(value: str) -> datetime:
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TAIPEI)
    return dt.astimezone(TAIPEI)


def split_label(day: str) -> str:
    if day <= "2024-12-31":
        return "DEVELOPMENT"
    if day <= "2025-12-31":
        return "VALIDATION"
    return "RESEARCH_TEST"


def half_label(day: str) -> str:
    y, m, _ = day.split("-")
    return f"{y}-H{1 if int(m) <= 6 else 2}"


def _num(v):
    try:
        return float(v)
    except Exception:
        return None


def extract_symbol_snapshots(payload: dict) -> list[tuple]:
    symbol = str(payload.get("symbol") or "")
    exchange = str(payload.get("exchange") or "")
    raw = payload.get("data") or []
    by_day = defaultdict(list)
    for b in raw:
        try:
            ts = parse_ts(b.get("date"))
        except Exception:
            continue
        by_day[ts.date().isoformat()].append((ts, b))

    days = sorted(by_day)
    out = []
    prev_close = None

    for day in days:
        items = sorted(by_day[day], key=lambda x: x[0])
        if not items:
            continue
        bm = {ts:b for ts,b in items}

        if prev_close is not None and prev_close > 0:
            prior_interval_start = datetime.fromisoformat(day + "T09:00:00").replace(tzinfo=TAIPEI)
            for obs in SCAN_TIMES:
                obs_dt = datetime.fromisoformat(day + "T" + obs + ":00").replace(tzinfo=TAIPEI)
                feature_bar = bm.get(obs_dt - timedelta(minutes=5))
                if feature_bar is None:
                    prior_interval_start = obs_dt
                    continue

                price = _num(feature_bar.get("close"))
                if price is None or price <= 0:
                    prior_interval_start = obs_dt
                    continue

                vol = 0.0
                any_vol = False
                for ts, b in items:
                    if prior_interval_start <= ts < obs_dt:
                        x = _num(b.get("volume"))
                        if x is not None:
                            vol += x
                            any_vol = True
                interval_minutes = (obs_dt - prior_interval_start).total_seconds() / 60.0
                vol_rate = (vol / interval_minutes) if any_vol and interval_minutes > 0 else None

                entry = exit_price = mfe = mae = None
                if obs in TRADE_TIMES:
                    hold_bars = []
                    complete = True
                    for j in range(6):
                        b = bm.get(obs_dt + timedelta(minutes=5*j))
                        if b is None:
                            complete = False
                            break
                        hold_bars.append(b)
                    if complete:
                        entry = _num(hold_bars[0].get("open"))
                        exit_price = _num(hold_bars[-1].get("close"))
                        highs = [_num(x.get("high")) for x in hold_bars]
                        lows = [_num(x.get("low")) for x in hold_bars]
                        highs = [x for x in highs if x is not None]
                        lows = [x for x in lows if x is not None]
                        if entry and entry > 0 and exit_price is not None and highs and lows:
                            mfe = max(highs) / entry - 1.0
                            mae = min(lows) / entry - 1.0
                        else:
                            entry = exit_price = mfe = mae = None

                day_return = price / prev_close - 1.0
                if price <= PRICE_CAP and day_return < DAY_RETURN_CAP:
                    out.append((
                        symbol, exchange, day, obs,
                        price, day_return, vol_rate,
                        entry, exit_price, mfe, mae,
                        split_label(day), half_label(day)
                    ))
                prior_interval_start = obs_dt

        closes = [_num(b.get("close")) for _, b in items]
        closes = [x for x in closes if x is not None and x > 0]
        if closes:
            prev_close = closes[-1]

    return out


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    PRAGMA temp_store=FILE;
    CREATE TABLE snapshots(
      symbol TEXT NOT NULL,
      exchange TEXT,
      session_date TEXT NOT NULL,
      obs TEXT NOT NULL,
      price REAL NOT NULL,
      day_return REAL NOT NULL,
      volume_rate REAL,
      entry REAL,
      exit REAL,
      mfe REAL,
      mae REAL,
      split TEXT,
      half TEXT
    );
    """)


def build_snapshot_db(history_root: str, db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    init_db(conn)
    files = sorted(Path(history_root).rglob("*_5m.json"))
    rows = 0
    symbols = set()
    errors = []
    for i, p in enumerate(files, 1):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            symbol = str(payload.get("symbol") or "")
            batch = extract_symbol_snapshots(payload)
            if batch:
                conn.executemany(
                    "INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch
                )
                rows += len(batch)
                symbols.add(symbol)
            if i % 100 == 0:
                conn.commit()
                print(f"snapshot files {i}/{len(files)} rows={rows}", flush=True)
        except Exception as exc:
            errors.append({"file":str(p), "error":f"{type(exc).__name__}: {exc}"})
    conn.commit()
    conn.execute("CREATE INDEX idx_snapshots_day_obs ON snapshots(session_date, obs)")
    conn.execute("CREATE INDEX idx_snapshots_symbol_day ON snapshots(symbol, session_date, obs)")
    conn.execute("""
      CREATE TABLE ranked AS
      SELECT *,
        ROW_NUMBER() OVER (
          PARTITION BY session_date, obs
          ORDER BY day_return DESC, symbol ASC
        ) AS gain_rank,
        COUNT(*) OVER (PARTITION BY session_date, obs) AS eligible_n
      FROM snapshots
    """)
    conn.execute("CREATE INDEX idx_ranked_day_obs_rank ON ranked(session_date,obs,gain_rank)")
    conn.execute("CREATE INDEX idx_ranked_symbol_day_obs ON ranked(symbol,session_date,obs)")
    conn.commit()
    report = {
        "files":len(files),
        "symbols":len(symbols),
        "snapshot_rows":rows,
        "parse_errors":errors[:100],
        "status":"PASS" if files and not errors else "FAIL",
    }
    conn.close()
    return report


def percentile_map(rows: list[dict], key: str) -> dict[str, float]:
    """Average-rank percentile for ties; frozen before outcome inspection."""
    ordered = sorted((float(r[key]), str(r["symbol"])) for r in rows)
    n = len(ordered)
    if n == 1:
        return {ordered[0][1]: 1.0}
    out = {}
    pos = 0
    while pos < n:
        j = pos + 1
        while j < n and ordered[j][0] == ordered[pos][0]:
            j += 1
        avg_rank = (pos + j - 1) / 2.0 / (n - 1)
        for k in range(pos, j):
            out[ordered[k][1]] = avg_rank
        pos = j
    return out


def select_trades(db_path: str) -> tuple[list[dict], dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    selected = []
    group_stats = []
    for obs in TRADE_TIMES:
        prev = PREV_SCAN[obs]
        elapsed = ELAPSED_MIN[obs]
        cur = conn.execute("""
          SELECT c.*, p.day_return AS prev_day_return,
                 p.gain_rank AS prev_gain_rank,
                 p.volume_rate AS prev_volume_rate
          FROM ranked c
          JOIN ranked p
            ON p.symbol=c.symbol
           AND p.session_date=c.session_date
           AND p.obs=?
          WHERE c.obs=? AND c.gain_rank<=100
          ORDER BY c.session_date, c.gain_rank, c.symbol
        """, (prev, obs))
        grouped = defaultdict(list)
        for row in cur:
            d = dict(row)
            vr = d.get("volume_rate")
            pvr = d.get("prev_volume_rate")
            if vr is None or pvr is None or pvr <= 0:
                continue
            d["price_velocity_per_min"] = (d["day_return"] - d["prev_day_return"]) / elapsed
            d["rank_velocity_per_min"] = (d["prev_gain_rank"] - d["gain_rank"]) / elapsed
            d["volume_acceleration"] = vr / pvr - 1.0
            if (
                d["price_velocity_per_min"] > 0
                and d["rank_velocity_per_min"] > 0
                and d["volume_acceleration"] > 0
            ):
                grouped[d["session_date"]].append(d)

        for day, candidates in grouped.items():
            p1 = percentile_map(candidates, "price_velocity_per_min")
            p2 = percentile_map(candidates, "rank_velocity_per_min")
            p3 = percentile_map(candidates, "volume_acceleration")
            for d in candidates:
                s = d["symbol"]
                d["velocity_score"] = (p1[s] + p2[s] + p3[s]) / 3.0
            candidates.sort(key=lambda x:(-x["velocity_score"], x["symbol"]))
            k = max(1, math.ceil(len(candidates) * 0.10))
            picks = candidates[:k]
            group_stats.append({
                "session_date":day, "obs":obs,
                "signal_candidates":len(candidates), "selected":len(picks)
            })
            for d in picks:
                if d.get("entry") and d.get("exit") and d["entry"] > 0:
                    gross = d["exit"] / d["entry"] - 1.0
                    d["gross_return"] = gross
                    d["net_return_045"] = gross - PRIMARY_COST
                    d["net_return_065"] = gross - STRESS_COST
                    d["outcome_status"] = "EVALUABLE"
                else:
                    d["gross_return"] = None
                    d["net_return_045"] = None
                    d["net_return_065"] = None
                    d["outcome_status"] = "NO_ENTRY_BAR"
                selected.append(d)
    conn.close()
    return selected, {
        "groups":len(group_stats),
        "group_stats":group_stats,
        "selected_rows":len(selected),
        "evaluable_rows":sum(1 for x in selected if x["outcome_status"]=="EVALUABLE"),
    }


def max_drawdown(trades: list[dict], field: str) -> float | None:
    baskets = defaultdict(list)
    for t in trades:
        v = t.get(field)
        if v is not None:
            baskets[(t["session_date"], t["obs"])].append(float(v))
    if not baskets:
        return None
    equity = peak = 1.0
    mdd = 0.0
    for key in sorted(baskets):
        r = sum(baskets[key]) / len(baskets[key])
        equity *= (1.0 + r)
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1.0)
    return mdd


def metrics(trades: list[dict], field: str) -> dict:
    vals = [float(x[field]) for x in trades if x.get(field) is not None]
    if not vals:
        return {"n":0}
    wins = [x for x in vals if x > 0]
    losses = [x for x in vals if x < 0]
    pf = (sum(wins) / abs(sum(losses))) if losses else None
    mfes = [float(x["mfe"]) for x in trades if x.get("mfe") is not None]
    maes = [float(x["mae"]) for x in trades if x.get("mae") is not None]
    return {
        "n":len(vals),
        "expectancy":sum(vals)/len(vals),
        "pf":pf,
        "win_rate":len(wins)/len(vals),
        "avg_win":sum(wins)/len(wins) if wins else None,
        "avg_loss":sum(losses)/len(losses) if losses else None,
        "max_drawdown":max_drawdown(trades, field),
        "avg_mfe":sum(mfes)/len(mfes) if mfes else None,
        "avg_mae":sum(maes)/len(maes) if maes else None,
    }


def subgroup_metrics(trades: list[dict], key: str, field: str) -> dict:
    groups = defaultdict(list)
    for t in trades:
        groups[str(t.get(key))].append(t)
    return {k:metrics(v, field) for k,v in sorted(groups.items())}


def adjudicate(primary: dict, by_split: dict, by_half: dict) -> str:
    if primary.get("n",0) < 200:
        return "HOLD_INSUFFICIENT_SAMPLE"
    if primary.get("expectancy") is None or primary["expectancy"] <= 0:
        return "REJECT_AFTER_COST_EXPECTANCY"
    if primary.get("pf") is None or primary["pf"] <= 1:
        return "REJECT_AFTER_COST_PF"
    for required in ("VALIDATION","RESEARCH_TEST"):
        m = by_split.get(required, {})
        if m.get("n",0) < 50:
            return "HOLD_SPLIT_SAMPLE"
        if m.get("expectancy") is None or m["expectancy"] <= 0 or (m.get("pf") or 0) <= 1:
            return "HOLD_SPLIT_INSTABILITY"
    eligible = [m for m in by_half.values() if m.get("n",0) >= 50]
    if len(eligible) < 3:
        return "HOLD_FOLD_SAMPLE"
    positive = sum(
        1 for m in eligible
        if m.get("expectancy") is not None and m["expectancy"] > 0 and (m.get("pf") or 0) > 1
    )
    if positive / len(eligible) < 0.67:
        return "HOLD_FOLD_INSTABILITY"
    return "PROMOTE_TO_SHADOW_CANDIDATE"


def write_trades(path: Path, rows: list[dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def run(history_root: str, out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    db_path = out / "top100_velocity_snapshots.sqlite"
    if db_path.exists():
        db_path.unlink()

    build = build_snapshot_db(history_root, str(db_path))
    trades, selection = select_trades(str(db_path))
    write_trades(out / "top100_velocity_selected_trades.csv", trades)

    overall_gross = metrics(trades, "gross_return")
    overall_045 = metrics(trades, "net_return_045")
    overall_065 = metrics(trades, "net_return_065")
    split_045 = subgroup_metrics(trades, "split", "net_return_045")
    half_045 = subgroup_metrics(trades, "half", "net_return_045")
    time_045 = subgroup_metrics(trades, "obs", "net_return_045")
    exchange_045 = subgroup_metrics(trades, "exchange", "net_return_045")

    counts = defaultdict(int)
    for t in trades:
        counts[t["symbol"]] += 1
    total = len(trades)
    concentration = {
        "unique_symbols":len(counts),
        "max_symbol_share":max(counts.values())/total if total else None,
        "top_symbols":sorted(
            ({"symbol":k,"n":v,"share":v/total} for k,v in counts.items()),
            key=lambda x:(-x["n"],x["symbol"])
        )[:20] if total else [],
    }

    decision = adjudicate(overall_045, split_045, half_045)
    report = {
        "schema_version":SCHEMA_VERSION,
        "preregistered_spec":"research/w5/TOP100_VELOCITY_BASELINE_PREREGISTRATION_20261026.md",
        "source":{
            "workflow_run_id":40221377923,
            "corrected_whole_universe_5m":True,
            "source_window":["2023-05-23","2026-10-22"],
        },
        "build":build,
        "selection":selection,
        "metrics":{
            "gross":overall_gross,
            "cost_045":overall_045,
            "cost_065":overall_065,
            "split_045":split_045,
            "half_045":half_045,
            "time_045":time_045,
            "exchange_045":exchange_045,
            "concentration":concentration,
        },
        "decision":decision,
        "governance":{
            "production_change":False,
            "historical_v14_comparison_performed":False,
            "freeze_family_retuned":False,
            "2026_fresh_oos_claim":False,
            "next_if_survives":"W4_PROSPECTIVE_SHADOW_CHAMPION_CHALLENGER",
        },
    }
    (out / "top100_velocity_baseline_a_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = [
        "# W2 Top100 Velocity Baseline A — Result",
        "",
        f"- Decision: **{decision}**",
        f"- Selected rows: {selection['selected_rows']:,}",
        f"- Evaluable rows: {selection['evaluable_rows']:,}",
        f"- Whole-universe source symbols parsed: {build['symbols']:,}",
        "",
        "## Primary 0.45% cost",
        "",
        f"- Expectancy: {overall_045.get('expectancy')}",
        f"- PF: {overall_045.get('pf')}",
        f"- Win rate: {overall_045.get('win_rate')}",
        f"- Max drawdown: {overall_045.get('max_drawdown')}",
        "",
        "## Stress 0.65% cost",
        "",
        f"- Expectancy: {overall_065.get('expectancy')}",
        f"- PF: {overall_065.get('pf')}",
        f"- Win rate: {overall_065.get('win_rate')}",
        "",
        "## Split 0.45%",
        "",
        json.dumps(split_045, ensure_ascii=False, indent=2),
        "",
        "## Half-year 0.45%",
        "",
        json.dumps(half_045, ensure_ascii=False, indent=2),
        "",
        "## Time-of-day 0.45%",
        "",
        json.dumps(time_045, ensure_ascii=False, indent=2),
        "",
        "No Production change. 2026 is Research Test, not fresh untouched OOS.",
    ]
    (out / "top100_velocity_baseline_a_report.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-root", required=True)
    ap.add_argument("--out-dir", default="research_output/top100_velocity_baseline_a")
    args = ap.parse_args()
    result = run(args.history_root, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
