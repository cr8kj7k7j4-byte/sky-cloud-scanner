from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def f(x, k):
    try:
        v = x.get(k)
        return None if v in (None, "") else float(v)
    except Exception:
        return None

def dt(s):
    return datetime.fromisoformat(str(s))

def group_days(obj):
    by = defaultdict(list)
    for b in obj["data"]:
        x = {**b, "_dt": dt(b["date"])}
        by[x["_dt"].date()].append(x)
    for d in by:
        by[d].sort(key=lambda z: z["_dt"])
    return by

def metrics(rows):
    if not rows:
        return {"n": 0}
    xs = [float(r["net_r"]) for r in rows]
    gp = sum(x for x in xs if x > 0)
    gl = -sum(x for x in xs if x < 0)
    return {
        "n": len(xs),
        "win_rate": sum(x > 0 for x in xs) / len(xs),
        "expectancy_r": statistics.mean(xs),
        "pf": gp / gl if gl else None,
    }

def bar_at_or_before(bars, hm):
    ans = None
    for b in bars:
        t = b["_dt"].strftime("%H:%M")
        if t > hm:
            break
        ans = b
    return ans

def percentile_rank(value, values):
    vals = sorted(v for v in values if v is not None and math.isfinite(v))
    if not vals:
        return None
    le = sum(v <= value for v in vals)
    return 100.0 * le / len(vals)

def bucket_gap(x):
    if x is None: return "UNKNOWN"
    if x < 0: return "LT_0"
    if x < 1: return "0_1"
    if x <= 3: return "1_3"
    return "GT_3"

def bucket_rs(x):
    if x is None: return "UNKNOWN"
    if x >= 1: return "GE_1"
    if x >= 0: return "0_1"
    if x >= -1: return "NEG1_0"
    return "LT_NEG1"

def bucket_peer(x):
    if x is None: return "UNKNOWN"
    if x >= 80: return "P80_100"
    if x >= 60: return "P60_79"
    if x >= 40: return "P40_59"
    return "LT_P40"

def bucket_vol(x):
    if x is None: return "UNKNOWN"
    if x >= 3: return "GE_3"
    if x >= 2: return "2_3"
    return "1_5_2"

def bucket_reaction(x):
    if x >= 80: return "80_100"
    if x >= 60: return "60_79"
    if x >= 40: return "40_59"
    return "LT_40"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default="research_output_stage6c")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with open(args.trades, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    bysym = {}
    for p in Path(args.data_dir).glob("*_5.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
        bysym[str(obj["symbol"])] = group_days(obj)

    enriched = []
    for r in rows:
        sym = str(r["symbol"])
        ad = datetime.fromisoformat(r["action_date"]).date()
        hm = r["trigger_time"]
        day = bysym.get(sym, {}).get(ad)
        if not day:
            continue

        stock_bar = bar_at_or_before(day, hm)
        stock_open = f(day[0], "open")
        stock_close = f(stock_bar or {}, "close")
        if not stock_open or stock_close is None:
            continue
        stock_ret = (stock_close / stock_open - 1.0) * 100.0

        rets = []
        for psym, days in bysym.items():
            pday = days.get(ad)
            if not pday:
                continue
            pb = bar_at_or_before(pday, hm)
            po = f(pday[0], "open")
            pc = f(pb or {}, "close")
            if po and pc is not None:
                rets.append((psym, (pc / po - 1.0) * 100.0))

        values = [x[1] for x in rets]
        if not values:
            continue
        breadth = 100.0 * sum(x > 0 for x in values) / len(values)
        medret = statistics.median(values)
        peer_pct = percentile_rank(stock_ret, values)
        rs = stock_ret - medret

        if breadth >= 60 and medret > 0:
            market_regime = "STRONG"
        elif breadth <= 40 and medret < 0:
            market_regime = "WEAK"
        else:
            market_regime = "NEUTRAL"

        gap = f(r, "gap_pct")
        vr = f(r, "volume_ratio")
        risk = f(r, "risk_pct")

        evidence = [
            breadth >= 55,
            rs > 0,
            peer_pct is not None and peer_pct >= 70,
            vr is not None and vr >= 2,
            gap is not None and 0 <= gap <= 3,
            risk is not None and risk <= 2,
        ]
        reaction_score = round(100.0 * sum(bool(x) for x in evidence) / len(evidence), 2)

        enriched.append({
            **r,
            "market_breadth_pct": round(breadth, 4),
            "market_median_intraday_ret_pct": round(medret, 4),
            "stock_intraday_ret_pct": round(stock_ret, 4),
            "relative_strength_pct": round(rs, 4),
            "peer_strength_proxy_pct": round(peer_pct, 4) if peer_pct is not None else None,
            "market_regime_proxy": market_regime,
            "gap_bucket": bucket_gap(gap),
            "rs_bucket": bucket_rs(rs),
            "peer_bucket": bucket_peer(peer_pct),
            "volume_bucket": bucket_vol(vr),
            "reaction_score": reaction_score,
            "reaction_bucket": bucket_reaction(reaction_score),
            "research_only": True,
            "trade_signal": False,
        })

    def by(field):
        vals = sorted({r[field] for r in enriched})
        return {v: metrics([r for r in enriched if r[field] == v]) for v in vals}

    # Coarse interaction signature. This is deliberately low-dimensional to reduce overfit.
    for r in enriched:
        r["interaction_signature"] = "|".join([
            "M+" if float(r["market_breadth_pct"]) >= 55 else "M-",
            "RS+" if float(r["relative_strength_pct"]) > 0 else "RS-",
            "P+" if float(r["peer_strength_proxy_pct"]) >= 70 else "P-",
            "V+" if f(r, "volume_ratio") is not None and f(r, "volume_ratio") >= 2 else "V-",
            "G+" if f(r, "gap_pct") is not None and 0 <= f(r, "gap_pct") <= 3 else "G-",
        ])

    interactions = []
    for sig in sorted({r["interaction_signature"] for r in enriched}):
        grp = [r for r in enriched if r["interaction_signature"] == sig]
        m = metrics(grp)
        y25 = metrics([r for r in grp if str(r["action_date"]).startswith("2025")])
        y26 = metrics([r for r in grp if str(r["action_date"]).startswith("2026")])
        stable_positive = (
            m.get("n",0) >= 30 and
            (m.get("expectancy_r") or -999) > 0 and
            (m.get("pf") or 0) > 1 and
            y25.get("n",0) >= 10 and y26.get("n",0) >= 10 and
            (y25.get("expectancy_r") or -999) > 0 and
            (y26.get("expectancy_r") or -999) > 0 and
            (y25.get("pf") or 0) > 1 and
            (y26.get("pf") or 0) > 1
        )
        interactions.append({
            "signature": sig,
            "all": m,
            "2025": y25,
            "2026": y26,
            "stable_positive_candidate": stable_positive,
        })

    interactions.sort(
        key=lambda x: (
            bool(x["stable_positive_candidate"]),
            x["all"].get("expectancy_r", -999),
            x["all"].get("n", 0),
        ),
        reverse=True,
    )

    report = {
        "scope": "Stage6C event x market x peer-strength-proxy x price-reaction interaction research",
        "trade_rows_input": len(rows),
        "trade_rows_enriched": len(enriched),
        "all": metrics(enriched),
        "by_market_regime_proxy": by("market_regime_proxy"),
        "by_peer_bucket": by("peer_bucket"),
        "by_relative_strength_bucket": by("rs_bucket"),
        "by_gap_bucket": by("gap_bucket"),
        "by_volume_bucket": by("volume_bucket"),
        "by_reaction_bucket": by("reaction_bucket"),
        "interaction_groups": interactions,
        "stable_positive_candidates": [x for x in interactions if x["stable_positive_candidate"]],
        "promotion_decision": "RESEARCH_ONLY",
        "limitations": [
            "No official historical industry mapping is available in the current manifest; peer_strength_proxy is a cross-sectional proxy, not a true sector score.",
            "The 100-symbol universe is drawn from the current listing universe and has survivorship bias.",
            "Interaction thresholds are candidate research definitions, not pre-registered production gates.",
            "A positive subgroup is not promotable without separate OOS, walk-forward, cost/slippage sensitivity and leakage review.",
            "Scores and buckets are research features, not probabilities or win-rate forecasts.",
        ],
    }

    (out / "stage6c_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if enriched:
        fields = sorted({k for r in enriched for k in r})
        with (out / "stage6c_trades.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(enriched)

    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
