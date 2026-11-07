"""Read-only Fugle Developer API entitlement smoke test.

No API key, token, response body, or exception URL is emitted to logs.
This verifies documented Fugle Developer REST endpoints, NOT market-wide
margin-maintenance data or individual account collateral maintenance.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
CHECKS = (
    ("listed_ticker", "/intraday/ticker/2330"),
    ("otc_ticker", "/intraday/ticker/6488"),
)


def probe(name: str, path: str, api_key: str) -> dict:
    """Make only documented GET requests and return sanitized metadata."""
    result = {"check": name, "http_status": None, "json_valid": False,
              "response_kind": None, "verified": False, "error_class": None}
    req = Request(BASE + path, headers={"X-API-KEY": api_key, "Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=15) as response:
            result["http_status"] = response.status
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                result["error_class"] = "RESPONSE_TOO_LARGE"
                return result
            try:
                payload = json.loads(raw)
                result["json_valid"] = True
                result["response_kind"] = type(payload).__name__
                result["verified"] = 200 <= response.status < 300 and isinstance(payload, (dict, list))
            except (ValueError, UnicodeError):
                result["error_class"] = "INVALID_JSON"
    except HTTPError as exc:
        result["http_status"] = exc.code
        result["error_class"] = "HTTP_ERROR"
    except (URLError, TimeoutError, OSError):
        result["error_class"] = "NETWORK_ERROR"
    return result


def main() -> int:
    key = os.getenv("FUGLE_API_KEY", "")
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "source": "FUGLE_DEVELOPER_REST", "tests": [], "developer_key_configured": bool(key),
              "margin_maintenance_endpoint_documented": False,
              "market_margin_maintenance_value": None, "status": "NOT_RUN"}
    if not key:
        report["status"] = "BLOCKED_MISSING_FUGLE_API_KEY"
    else:
        report["tests"] = [probe(name, path, key) for name, path in CHECKS]
        report["status"] = "PASS" if all(x["verified"] for x in report["tests"]) else "FAIL_OR_PARTIAL"
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
