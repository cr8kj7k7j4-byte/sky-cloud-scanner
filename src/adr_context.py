from __future__ import annotations

import os
import requests

ALPHA_URL = "https://www.alphavantage.co/query"
ADR_MAP = {
    "TSM": {"tw_symbol": "2330", "name": "台積電ADR"},
    "UMC": {"tw_symbol": "2303", "name": "聯電ADR"},
}

def _quote(symbol, api_key):
    r = requests.get(
        ALPHA_URL,
        params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    q = payload.get("Global Quote") or {}
    if not q:
        note = payload.get("Note") or payload.get("Information") or "empty quote"
        raise RuntimeError(str(note))
    price = q.get("05. price")
    change_pct = str(q.get("10. change percent") or "").replace("%", "").strip()
    if price in (None, ""):
        raise RuntimeError("missing price")
    return {
        "price": float(price),
        "change_pct": float(change_pct) if change_pct not in ("", None) else None,
        "latest_trading_day": q.get("07. latest trading day"),
    }

def fetch_taiwan_adr_context():
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "NOT_CONNECTED",
            "provider": "ALPHAVANTAGE",
            "reason": "ALPHAVANTAGE_API_KEY_NOT_SET",
            "quotes": [],
            "trade_signal": False,
        }

    quotes, errors = [], []
    for adr, meta in ADR_MAP.items():
        try:
            q = _quote(adr, api_key)
            quotes.append({
                "adr_symbol": adr,
                "tw_symbol": meta["tw_symbol"],
                "name": meta["name"],
                **q,
                "source": "ALPHAVANTAGE",
                "trade_signal": False,
            })
        except Exception as exc:
            errors.append({"adr_symbol": adr, "error": f"{type(exc).__name__}: {exc}"})

    return {
        "status": "CONNECTED" if quotes else "ERROR",
        "provider": "ALPHAVANTAGE",
        "quotes": quotes,
        "errors": errors,
        "trade_signal": False,
        "note": "ADR 僅作隔夜關聯證據，不直接形成台股買進訊號",
    }
