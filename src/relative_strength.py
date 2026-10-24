from collections import defaultdict
from statistics import mean


def apply_relative_strength(rows, group_key="sector"):
    rows = rows or []
    grouped = defaultdict(list)

    for row in rows:
        group = row.get(group_key) or row.get("exchange") or "UNKNOWN"
        if row.get("change_pct") is not None:
            grouped[group].append(float(row["change_pct"]))

    group_mean = {
        key: mean(values)
        for key, values in grouped.items()
        if values
    }

    enriched = []
    for row in rows:
        x = dict(row)
        group = x.get(group_key) or x.get("exchange") or "UNKNOWN"
        base = group_mean.get(group)
        cp = x.get("change_pct")
        rs = None
        if cp is not None and base is not None:
            rs = float(cp) - float(base)
        x["rs_group"] = group
        x["rs_group_mean_pct"] = round(base, 3) if base is not None else None
        x["relative_strength_score"] = round(rs, 3) if rs is not None else None
        enriched.append(x)

    enriched.sort(
        key=lambda r: (
            r.get("relative_strength_score") is not None,
            r.get("relative_strength_score") or -9999,
            r.get("trade_value") or 0,
        ),
        reverse=True,
    )
    return enriched
