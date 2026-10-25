from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.intraday_replay_validator import CANONICAL_RULE_COLUMNS


def _profit_factor(values) -> float | str:
    vals = np.asarray(values, dtype=float)
    gains = vals[vals > 0].sum()
    losses = abs(vals[vals < 0].sum())
    if losses == 0:
        return "inf" if gains > 0 else 0.0
    return round(float(gains / losses), 6)


def _ordered_values(df: pd.DataFrame, outcome_column: str) -> np.ndarray:
    x = df.copy()
    for col in ("decision_timestamp", "observation_timestamp", "session_date"):
        if col in x.columns:
            x["_order"] = pd.to_datetime(x[col], errors="coerce", utc=True)
            x = x.sort_values("_order", kind="stable")
            break
    return pd.to_numeric(x[outcome_column], errors="coerce").dropna().to_numpy(float)


def _max_drawdown_r(values) -> float:
    vals = np.asarray(values, dtype=float)
    if vals.size == 0:
        return 0.0
    equity = np.cumsum(vals)
    equity_with_origin = np.concatenate(([0.0], equity))
    peaks = np.maximum.accumulate(equity_with_origin)
    drawdown = equity_with_origin - peaks
    return round(float(abs(drawdown.min())), 6)


def _mean_optional(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return round(float(s.mean()), 6) if not s.empty else None


def _rate_optional(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns or df.empty:
        return None
    s = df[col].dropna()
    if s.empty:
        return None
    if s.dtype == bool:
        return round(float(s.mean()), 6)
    normalized = s.map(lambda x: str(x).strip().lower() in {"1", "true", "yes", "y"})
    return round(float(normalized.mean()), 6)


def evaluate_subset(df: pd.DataFrame, outcome_column: str) -> dict:
    if outcome_column not in df.columns:
        raise ValueError(f"missing outcome column: {outcome_column}")

    r = _ordered_values(df, outcome_column)
    if r.size == 0:
        return {
            "n": 0,
            "win_rate": 0.0,
            "avg_win_r": None,
            "avg_loss_r": None,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
            "avg_mae_r": None,
            "avg_mfe_r": None,
            "avg_r_multiple": None,
            "false_breakout_rate": None,
            "missed_entry_rate": None,
            "avg_slippage_bps": None,
            "cost_adjusted_return_r": 0.0,
        }

    wins = r[r > 0]
    losses = r[r < 0]
    return {
        "n": int(r.size),
        "win_rate": round(float(np.mean(r > 0)), 6),
        "avg_win_r": round(float(wins.mean()), 6) if wins.size else None,
        "avg_loss_r": round(float(losses.mean()), 6) if losses.size else None,
        "expectancy_r": round(float(r.mean()), 6),
        "profit_factor": _profit_factor(r),
        "max_drawdown_r": _max_drawdown_r(r),
        "avg_mae_r": _mean_optional(df, "mae_r"),
        "avg_mfe_r": _mean_optional(df, "mfe_r"),
        "avg_r_multiple": _mean_optional(df, "r_multiple"),
        "false_breakout_rate": _rate_optional(df, "false_breakout"),
        "missed_entry_rate": _rate_optional(df, "missed_entry"),
        "avg_slippage_bps": _mean_optional(df, "actual_slippage_bps")
        if "actual_slippage_bps" in df.columns
        else (
            round(
                float(
                    pd.concat(
                        [
                            pd.to_numeric(df.get("actual_entry_slippage_bps"), errors="coerce"),
                            pd.to_numeric(df.get("actual_exit_slippage_bps"), errors="coerce"),
                        ]
                    ).dropna().mean()
                ),
                6,
            )
            if (
                "actual_entry_slippage_bps" in df.columns
                and "actual_exit_slippage_bps" in df.columns
                and not pd.concat(
                    [
                        pd.to_numeric(df["actual_entry_slippage_bps"], errors="coerce"),
                        pd.to_numeric(df["actual_exit_slippage_bps"], errors="coerce"),
                    ]
                ).dropna().empty
            )
            else None
        ),
        "cost_adjusted_return_r": round(float(r.sum()), 6),
    }


def _pf_number(value) -> float:
    return 999.0 if value == "inf" else float(value or 0.0)


def contribution(full: dict, without_rule: dict) -> dict:
    ablated_n = int(without_rule["n"])
    full_n = int(full["n"])
    reduced_count = max(0, ablated_n - full_n)
    return {
        "expectancy_contribution": round(
            float(full["expectancy_r"]) - float(without_rule["expectancy_r"]), 6
        ),
        "profit_factor_contribution": round(
            _pf_number(full["profit_factor"])
            - _pf_number(without_rule["profit_factor"]),
            6,
        ),
        "drawdown_protection": round(
            float(without_rule["max_drawdown_r"])
            - float(full["max_drawdown_r"]),
            6,
        ),
        "sample_reduction_count": reduced_count,
        "sample_reduction_share": round(
            reduced_count / ablated_n if ablated_n else 0.0,
            6,
        ),
    }


def _coerce_gate(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.map(lambda x: str(x).strip().lower() in {"1", "true", "yes", "y"})


def apply_rules(
    df: pd.DataFrame,
    *,
    disabled: list[str] | None = None,
    rules: list[str] | None = None,
) -> pd.DataFrame:
    rules = rules or CANONICAL_RULE_COLUMNS
    disabled_set = set(disabled or [])
    mask = pd.Series(True, index=df.index)
    for rule in rules:
        if rule in disabled_set:
            continue
        if rule not in df.columns:
            raise ValueError(f"missing rule column: {rule}")
        mask &= _coerce_gate(df[rule])
    return df.loc[mask].copy()


def _derive_time_of_day(df: pd.DataFrame) -> pd.DataFrame:
    if "time_of_day" in df.columns or "decision_timestamp" not in df.columns:
        return df
    x = df.copy()
    ts = pd.to_datetime(x["decision_timestamp"], errors="coerce")
    minute = ts.dt.hour * 60 + ts.dt.minute
    x["time_of_day"] = pd.cut(
        minute,
        bins=[0, 569, 599, 659, 719, 1439],
        labels=["preopen_or_unknown", "09:00-09:59", "10:00-10:59", "11:00-11:59", "12:00+"],
        include_lowest=True,
    ).astype(str)
    return x


def slice_metrics(df: pd.DataFrame, outcome_column: str) -> dict:
    x = _derive_time_of_day(df)
    dimensions = [
        "market_regime",
        "time_of_day",
        "liquidity_bucket",
        "spread_bucket",
        "slippage_bucket",
        "trigger_quality",
        "false_breakout",
        "missed_entry",
        "execution_rr_bucket",
        "ranking_decile",
        "capacity_bucket",
    ]
    out = {}
    for dim in dimensions:
        if dim not in x.columns:
            continue
        rows = {}
        for key, part in x.groupby(dim, dropna=False):
            rows[str(key)] = evaluate_subset(part, outcome_column)
        out[dim] = rows
    return out


def concentration_metrics(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {
            "single_symbol_max_share": 0.0,
            "sector_max_share": 0.0,
            "top_symbol": None,
            "top_sector": None,
        }

    symbol_counts = df["symbol"].value_counts(dropna=False) if "symbol" in df.columns else pd.Series(dtype=int)
    sector_counts = df["sector"].value_counts(dropna=False) if "sector" in df.columns else pd.Series(dtype=int)

    return {
        "single_symbol_max_share": round(float(symbol_counts.iloc[0] / n), 6)
        if not symbol_counts.empty else None,
        "sector_max_share": round(float(sector_counts.iloc[0] / n), 6)
        if not sector_counts.empty else None,
        "top_symbol": str(symbol_counts.index[0]) if not symbol_counts.empty else None,
        "top_sector": str(sector_counts.index[0]) if not sector_counts.empty else None,
    }


def candidate_diagnostics(df: pd.DataFrame) -> dict:
    return {
        "candidate_n": int(len(df)),
        "trigger_frequency": _rate_optional(df, "trigger_gate"),
        "false_breakout_rate": _rate_optional(df, "false_breakout"),
        "missed_entry_rate": _rate_optional(df, "missed_entry"),
        "avg_entry_slippage_bps": _mean_optional(df, "actual_entry_slippage_bps"),
        "avg_exit_slippage_bps": _mean_optional(df, "actual_exit_slippage_bps"),
    }


def run_ablation(df: pd.DataFrame, *, outcome_column: str) -> dict:
    missing = sorted(
        set(CANONICAL_RULE_COLUMNS + [outcome_column]) - set(df.columns)
    )
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    full_df = apply_rules(df)
    full = evaluate_subset(full_df, outcome_column)
    report = {
        "outcome_column": outcome_column,
        "rules": CANONICAL_RULE_COLUMNS,
        "candidate_diagnostics": candidate_diagnostics(df),
        "full_metrics": full,
        "full_concentration": concentration_metrics(full_df),
        "full_slices": slice_metrics(full_df, outcome_column),
        "single_rule_ablation": {},
        "production_eligible": False,
    }

    for rule in CANONICAL_RULE_COLUMNS:
        without_df = apply_rules(df, disabled=[rule])
        without = evaluate_subset(without_df, outcome_column)
        report["single_rule_ablation"][rule] = {
            "without_rule_metrics": without,
            "delta_vs_full": contribution(full, without),
            "without_rule_concentration": concentration_metrics(without_df),
        }

    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument(
        "--outcome-column",
        choices=["net_r_045", "net_r_065"],
        default="net_r_045",
    )
    ap.add_argument("--out", default="research_output/intraday_rule_ablation.json")
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    report = run_ablation(df, outcome_column=args.outcome_column)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
