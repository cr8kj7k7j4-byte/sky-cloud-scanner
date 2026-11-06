"""Nova local quote intake: read-only, safe to run offline with mocked responses.

Usage (local Windows, with licensed SDK and certificate; never commit credentials):
  python tools/nova_quote_probe.py --symbols 2330 8088 --output nova_probe.json

The script asks for credentials without echo; emits *only* quote data and diagnostic codes.
Never upload the PFX, tokens, account IDs, stdout containing secrets, or this output
unless the account's vendor data-sharing terms permit it.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from typing import Any


def _dict(data: Any) -> dict:
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump()
    if hasattr(data, "dict"):
        return data.dict()
    raise TypeError("QUOTE_UNSUPPORTED_RESPONSE")


def normalize(symbol: str, response: Any, observed_at: str) -> dict:
    data = _dict(response)
    total = data.get("total") or {}
    if not isinstance(total, dict):
        total = {}
    quote = {
        "requested_symbol": symbol,
        "symbol": data.get("symbol"),
        "date": data.get("date"),
        "close_price": data.get("closePrice"),
        "close_time": data.get("closeTime"),
        "last_updated": data.get("lastUpdated"),
        "market": data.get("market"),
        "exchange": data.get("exchange"),
        "trade_volume_raw": total.get("tradeVolume"),
        "observed_at_utc": observed_at,
    }
    quote["valid_basic_quote"] = (
        str(quote["symbol"]) == symbol
        and bool(quote["date"])
        and isinstance(quote["close_price"], (float, int))
        and quote["close_price"] > 0
    )
    return quote


def run(symbols: list[str], cert: Path) -> dict:
    # Imported lazily so normalization tests do not require licensed packages.
    from taishin_sdk import TaishinSDK

    if not cert.is_file() or cert.suffix.lower() != ".pfx":
        raise ValueError("CERT_NOT_FOUND")
    user_id = getpass("證券登入身分證字號：")
    password = getpass("證券登入密碼：")
    cert_password = getpass("憑證密碼：")
    try:
        sdk = TaishinSDK()
        accounts = sdk.login(user_id, password, str(cert), cert_password)
        if not accounts:
            raise RuntimeError("LOGIN_NO_ACCOUNTS")
        sdk.init_realtime(accounts[0])
        stock = sdk.marketdata.rest_client.stock
        results = []
        for symbol in symbols:
            observed = datetime.now(timezone.utc).isoformat()
            try:
                q = stock.intraday.quote(symbol=symbol)
                results.append(normalize(symbol, q, observed))
            except Exception as exc:
                # Do not serialize provider exceptions: they may contain tokens/PII.
                results.append({"requested_symbol": symbol, "valid_basic_quote": False,
                                "error_type": type(exc).__name__, "observed_at_utc": observed})
        return {"schema": "SKY_NOVA_LOCAL_PROBE_V1", "source": "NOVA_LOCAL",
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "count": len(symbols), "quotes": results,
                "notice": "Basic quote != realtime freshness or full-market coverage."}
    finally:
        user_id = password = cert_password = None


def main() -> None:
    p = argparse.ArgumentParser(description="Read-only local Nova quote probe")
    p.add_argument("--symbols", nargs="+", default=["2330", "8088"])
    p.add_argument("--cert", type=Path, default=None)
    p.add_argument("--output", type=Path, default=Path("nova_probe.json"))
    args = p.parse_args()
    cert = args.cert
    if cert is None:
        candidates = list((Path.home() / "Desktop").glob("*.pfx"))
        if len(candidates) != 1:
            raise SystemExit("CERT_FILE_CHECK_FAILED: provide --cert locally")
        cert = candidates[0]
    try:
        report = run(args.symbols, cert)
    except Exception as exc:
        print("PROBE_FAILED", type(exc).__name__)
        raise SystemExit(2)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("PROBE_FINISHED", sum(q.get("valid_basic_quote", False) for q in report["quotes"]), "/", report["count"])
    print("OUTPUT", args.output)


if __name__ == "__main__":
    main()
