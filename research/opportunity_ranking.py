from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Research-only defaults. These are NOT production weights.
DEFAULT_POSITIVE_WEIGHTS: Dict[str, float] = {
    "intraday_momentum": 1.0,
    "market_relative_strength": 1.0,
    "sector_relative_strength": 1.0,
    "volume_anomaly": 1.0,
    "vwap_structure": 1.0,
    "breakout_quality": 1.0,
    "entry_quality": 1.0,
    "net_rr": 1.0,
}

DEFAULT_PENALTY_WEIGHTS: Dict[str, float] = {
    "anti_chase_risk": 1.0,
    "liquidity_slippage_risk": 1.0,
}


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile_ranks(values: List[Tuple[int, float]]) -> Dict[int, float]:
    """Return 0..1 percentile ranks using average rank for ties."""
    if not values:
        return {}
    ordered = sorted(values, key=lambda x: x[1])
    out: Dict[int, float] = {}
    n = len(ordered)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        avg_position = (i + j) / 2
        pct = 1.0 if n == 1 else avg_position / (n - 1)
        for k in range(i, j + 1):
            out[ordered[k][0]] = pct
        i = j + 1
    return out


def rank_snapshot(
    rows: List[dict],
    positive_weights: Dict[str, float] | None = None,
    penalty_weights: Dict[str, float] | None = None,
    gate_field: str = "gate_pass",
) -> List[dict]:
    """
    Rank only Gate-qualified candidates within one snapshot.

    opportunity_score is a relative opportunity-quality score, NOT a
    probability of price appreciation or a statistical win rate.
    """
    positive_weights = positive_weights or DEFAULT_POSITIVE_WEIGHTS
    penalty_weights = penalty_weights or DEFAULT_PENALTY_WEIGHTS

    eligible = []
    for row in rows:
        raw = str(row.get(gate_field, "true")).strip().lower()
        if raw in {"1", "true", "yes", "y", "pass", "passed"}:
            eligible.append(dict(row))

    if not eligible:
        return []

    feature_pct: Dict[str, Dict[int, float]] = {}
    for feature in list(positive_weights) + list(penalty_weights):
        vals = []
        for idx, row in enumerate(eligible):
            value = _to_float(row.get(feature))
            if value is not None:
                vals.append((idx, value))
        feature_pct[feature] = percentile_ranks(vals)

    scored = []
    for idx, row in enumerate(eligible):
        weighted_sum = 0.0
        total_weight = 0.0

        for feature, weight in positive_weights.items():
            pct = feature_pct[feature].get(idx)
            if pct is not None and weight > 0:
                weighted_sum += pct * weight
                total_weight += weight

        for feature, weight in penalty_weights.items():
            pct = feature_pct[feature].get(idx)
            if pct is not None and weight > 0:
                weighted_sum += (1.0 - pct) * weight
                total_weight += weight

        if total_weight == 0:
            continue

        row["opportunity_score"] = round(100.0 * weighted_sum / total_weight, 2)
        scored.append(row)

    scored.sort(
        key=lambda r: (
            -float(r["opportunity_score"]),
            str(r.get("symbol", "")),
        )
    )
    for rank, row in enumerate(scored, start=1):
        row["opportunity_rank"] = rank

    return scored


def rank_rows(
    rows: Iterable[dict],
    group_fields: Tuple[str, ...] = ("day", "scan_time"),
    gate_field: str = "gate_pass",
) -> List[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field, "") for field in group_fields)
        groups[key].append(row)

    out = []
    for key in sorted(groups):
        out.extend(rank_snapshot(groups[key], gate_field=gate_field))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Sky P0-O research-only cross-sectional opportunity ranking"
    )
    ap.add_argument("--input", required=True, help="Input candidate CSV")
    ap.add_argument("--out", default="research_output/opportunity_ranking.csv")
    ap.add_argument("--gate-field", default="gate_pass")
    args = ap.parse_args()

    src = Path(args.input)
    with src.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ranked = rank_rows(rows, gate_field=args.gate_field)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not ranked:
        out.write_text("", encoding="utf-8")
        print("No Gate-qualified candidates with rankable features.")
        return

    fields = list(ranked[0].keys())
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(ranked)

    print(f"Wrote {len(ranked)} ranked candidate rows to {out}")


if __name__ == "__main__":
    main()
