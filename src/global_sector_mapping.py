from __future__ import annotations

SECTOR_RULES = {
    "SEMICONDUCTOR": {
        "label": "半導體",
        "positive": ("nasdaq_up", "sp500_up", "vix_low", "ntd_weak", "tsm_adr_up", "umc_adr_up"),
        "negative": ("nasdaq_down", "vix_high", "us10y_high", "ntd_strong", "tsm_adr_down", "umc_adr_down", "bis_policy_risk"),
    },
    "AI_SERVER": {
        "label": "AI／伺服器",
        "positive": ("nasdaq_up", "sp500_up", "vix_low", "ntd_weak", "tsm_adr_up"),
        "negative": ("nasdaq_down", "vix_high", "us10y_high", "tsm_adr_down", "bis_policy_risk"),
    },
    "DISPLAY": {
        "label": "面板",
        "positive": ("sp500_up", "ntd_weak", "wti_low"),
        "negative": ("sp500_down", "vix_high", "wti_high"),
    },
    "FINANCIAL": {
        "label": "金融",
        "positive": ("sp500_up", "us10y_high", "vix_low"),
        "negative": ("sp500_down", "vix_high"),
    },
}

def _num(v):
    try:
        return float(v)
    except Exception:
        return None

def _flags(ctx):
    flags = set()
    vix = _num((ctx.get("vix") or {}).get("value"))
    us10y = _num((ctx.get("us10y") or {}).get("value"))
    wti = _num((ctx.get("wti") or {}).get("value"))
    ntdusd = _num((ctx.get("ntdusd") or {}).get("value"))
    adr_quotes = ((ctx.get("adr_context") or {}).get("quotes") or [])
    bis_events = ctx.get("bis_policy_events") or []

    # Current-value context only. Directional daily moves are not inferred
    # unless a verified previous observation is available.
    if vix is not None:
        if vix < 18: flags.add("vix_low")
        if vix >= 25: flags.add("vix_high")
    if us10y is not None:
        if us10y >= 4.5: flags.add("us10y_high")
        if us10y <= 3.5: flags.add("us10y_low")
    if wti is not None:
        if wti >= 90: flags.add("wti_high")
        if wti <= 65: flags.add("wti_low")
    if ntdusd is not None:
        if ntdusd >= 32.5: flags.add("ntd_weak")
        if ntdusd <= 30.5: flags.add("ntd_strong")

    for q in adr_quotes:
        sym = str(q.get("adr_symbol") or "").upper()
        chg = _num(q.get("change_pct"))
        if chg is None:
            continue
        if sym == "TSM":
            flags.add("tsm_adr_up" if chg > 0 else "tsm_adr_down" if chg < 0 else "tsm_adr_flat")
        if sym == "UMC":
            flags.add("umc_adr_up" if chg > 0 else "umc_adr_down" if chg < 0 else "umc_adr_flat")

    if bis_events:
        flags.add("bis_policy_risk")

    # Index levels alone do not imply up/down. Leave directional flags absent
    # until change data is separately verified.
    return flags

def map_global_context_to_sectors(ctx):
    flags = _flags(ctx or {})
    out = []
    for key, rule in SECTOR_RULES.items():
        pos = [x for x in rule["positive"] if x in flags]
        neg = [x for x in rule["negative"] if x in flags]
        score = 50 + 8 * len(pos) - 10 * len(neg)
        score = max(0, min(100, score))
        if score >= 60:
            bias = "FAVORABLE"
        elif score <= 40:
            bias = "UNFAVORABLE"
        else:
            bias = "NEUTRAL"
        out.append({
            "sector_key": key,
            "sector": rule["label"],
            "context_score": score,
            "bias": bias,
            "positive_factors": pos,
            "negative_factors": neg,
            "trade_signal": False,
            "note": "僅為盤前全球背景映射，不代表族群一定上漲或下跌",
        })
    return out
