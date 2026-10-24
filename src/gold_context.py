from __future__ import annotations

import os
import requests

GOLDAPI_URL = "https://www.goldapi.io/api/XAU/USD"

def fetch_gold_context():
    token = os.getenv("GOLDAPI_TOKEN", "").strip()
    if not token:
        return {
            "status": "NOT_CONNECTED",
            "provider": "GOLDAPI_IO",
            "reason": "GOLDAPI_TOKEN_NOT_SET",
            "quote": None,
            "trade_signal": False,
        }

    try:
        r = requests.get(
            GOLDAPI_URL,
            headers={"x-access-token": token, "User-Agent": "SkyPremarketGold/1.0"},
            timeout=30,
        )
        r.raise_for_status()
        p = r.json()
        price = p.get("price")
        if price is None:
            raise RuntimeError("missing gold price")
        change_pct = p.get("change_percent")
        if change_pct is None:
            change_pct = p.get("chp")
        return {
            "status": "CONNECTED",
            "provider": "GOLDAPI_IO",
            "quote": {
                "key": "XAUUSD",
                "name": "黃金現貨 XAU/USD",
                "value": float(price),
                "unit": "USD/troy_ounce",
                "change_pct": float(change_pct) if change_pct is not None else None,
                "as_of": p.get("datetime") or p.get("timestamp"),
                "source": "GOLDAPI_IO",
                "source_url": GOLDAPI_URL,
                "trade_signal": False,
            },
            "trade_signal": False,
            "note": "黃金僅作全球避險與通膨背景，不直接形成台股交易訊號",
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "provider": "GOLDAPI_IO",
            "reason": f"{type(exc).__name__}: {exc}",
            "quote": None,
            "trade_signal": False,
        }
