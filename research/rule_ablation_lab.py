from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


RULE_COLUMNS = [
    "market_gate",
    "sector_rs_gate",
    "anti_chase_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "rr_gate",
]


def _profit_factor(values):
    vals = np.asarray(values, dtype=float)
    gains = vals[vals > 0].sum()
    losses = abs(vals[vals < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown_r(values):
    vals = np.asarray(values, dtype=float)
    if vals.size == 0:
        return 0.0
    equity = np.cumsum(vals)
    peaks = np.maximum.accumulate(equity)
    dd = equity - peaks
    return float(abs(dd.min()))


def evaluate_subset(df):
    if df.empty:
        return {
            "n": 0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
            "positive_rate": 0.0,
        }
    r = pd.to_numeric(df["net_r"], errors="coerce").dropna().to_numpy(float)
    if r.size == 0:
        return {
            "n": 0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
            "positive_rate": 0.0,
        }
    pf = _profit_factor(r)
    return {
        "n": int(len(r)),
        "expectancy_r": round(float(r.mean()), 6),
        "profit_factor": round(pf, 6) if np.isfinite(pf) else "inf",
        "max_drawdown_r": round(_max_drawdown_r(r), 6),
        "positive_rate": round(float(np.mean(r > 0)), 6),
    }


def _pf(v):
    return 999.0 if v == "inf" else float(v or 0.0)


def compare(full, ablated):
    return {
        "expectancy_contribution": round(
            float(full["expectancy_r"]) - float(ablated["expectancy_r"]), 6
        ),
        "profit_factor_contribution": round(
            _pf(full["profit_factor"]) - _pf(ablated["profit_factor"]), 6
        ),
        "drawdown_protection": round(
            abs(float(ablated["max_drawdown_r"])) - abs(float(full["max_drawdown_r"])),
            6,
        ),
        "trade_count_delta": int(full["n"]) - int(ablated["n"]),
    }


def _apply_rules(df, disabled=None):
    disabled = set(disabled or [])
    mask = pd.Series(True, index=df.index)
    for rule in RULE_COLUMNS:
        if rule in disabled:
            continue
        if rule not in df.columns:
            raise ValueError(f"missing rule column: {rule}")
        mask &= df[rule].astype(bool)
    return df[mask].copy()


def regime_summary(df):
    if "regime" not in df.columns:
        return {}
    out = {}
    for regime, part in df.groupby("regime"):
        out[str(regime)] = evaluate_subset(part)
    return out


def run_rule_ablation(df):
    needed = set(RULE_COLUMNS + ["net_r"])
    missing = sorted(needed - set(df.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    full_df = _apply_rules(df)
    full = evaluate_subset(full_df)
    report = {
        "full_rules": RULE_COLUMNS,
        "full_metrics": full,
        "full_regime": regime_summary(full_df),
        "single_rule_ablation": {},
        "production_eligible": False,
        "note": (
            "Rule ablation is research evidence only. No production gate may be "
            "removed from one experiment."
        ),
    }

    for rule in RULE_COLUMNS:
        ablated_df = _apply_rules(df, disabled=[rule])
        metrics = evaluate_subset(ablated_df)
        report["single_rule_ablation"][rule] = {
            "metrics": metrics,
            "delta_vs_full": compare(full, metrics),
            "regime": regime_summary(ablated_df),
        }

    return report


def classify_rule(delta, regime_consistent=False, walk_forward_consistent=False):
    exp = float(delta.get("expectancy_contribution") or 0.0)
    pf = float(delta.get("profit_factor_contribution") or 0.0)
    dd = float(delta.get("drawdown_protection") or 0.0)

    if exp > 0 and (pf > 0 or dd > 0) and regime_consistent and walk_forward_consistent:
        return "KEEP"
    if exp < 0 and pf < 0 and dd < 0:
        return "PRUNE_CANDIDATE"
    return "RESEARCH_MORE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default="research_output/rule_ablation.json")
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    report = run_rule_ablation(df)
    for rule, item in report["single_rule_ablation"].items():
        item["governance_status"] = classify_rule(item["delta_vs_full"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
