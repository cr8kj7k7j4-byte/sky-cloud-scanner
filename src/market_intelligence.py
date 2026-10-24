from statistics import mean


def summarize_market(rows):
    rows = [r for r in (rows or []) if r.get("change_pct") is not None]
    if not rows:
        return {
            "status": "INSUFFICIENT_DATA",
            "breadth_pct": None,
            "median_change_pct": None,
            "market_bias": "UNKNOWN",
            "leaders": [],
        }

    changes = sorted(float(r["change_pct"]) for r in rows)
    adv = sum(1 for x in changes if x > 0)
    dec = sum(1 for x in changes if x < 0)
    flat = len(changes) - adv - dec
    breadth = adv / len(changes) * 100.0
    mid = len(changes) // 2
    median = changes[mid] if len(changes) % 2 else (changes[mid - 1] + changes[mid]) / 2

    if breadth >= 60 and median > 0:
        bias = "BULLISH"
    elif breadth <= 40 and median < 0:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    leaders = sorted(
        rows,
        key=lambda r: (float(r.get("trade_value") or 0), float(r.get("change_pct") or 0)),
        reverse=True,
    )[:10]

    return {
        "status": "OK",
        "count": len(rows),
        "advancers": adv,
        "decliners": dec,
        "flat": flat,
        "breadth_pct": round(breadth, 2),
        "average_change_pct": round(mean(changes), 3),
        "median_change_pct": round(median, 3),
        "market_bias": bias,
        "leaders": [
            {
                "symbol": x.get("symbol"),
                "name": x.get("name"),
                "change_pct": x.get("change_pct"),
                "trade_value": x.get("trade_value"),
            }
            for x in leaders
        ],
        "note": "P0-M 僅描述市場狀態，不直接形成買進訊號",
    }
