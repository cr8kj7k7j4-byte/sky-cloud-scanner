"""Canonical, endpoint-level request identity for bounded Fugle market-data work.

The key deliberately excludes GitHub workflow/run identity. Distinct data
queries must not share reservations; equivalent query syntax must normalize.
Unknown routes are rejected instead of receiving an unsafe global identity.
This module is offline: it never sends market-data requests.
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import parse_qsl, urlsplit

SAFE_ENDPOINT = re.compile(r"^/(?:marketdata/v1\.0/stock/)?(snapshot/quotes/(?:TSE|OTC)|intraday/(?:quote|candles)/[0-9A-Za-z]+|historical/candles/[0-9A-Za-z]+)$")
SAFE_SYMBOL = re.compile(r"^[0-9A-Za-z]{2,10}$")
ALLOWED_PARAMETERS = frozenset({"from", "to", "timeframe", "type", "limit", "sort", "offset"})


def canonical_fugle_request(method: str, url: str, *, parameters: dict | None = None) -> str:
    if not isinstance(method, str) or method.upper() != "GET":
        raise ValueError("ONLY_READ_ONLY_GET_SUPPORTED")
    if not isinstance(url, str):
        raise ValueError("INVALID_FUGLE_URL")
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("UNSAFE_FUGLE_URL")
    if parsed.scheme and (parsed.scheme != "https" or parsed.hostname != "api.fugle.tw"):
        raise ValueError("UNTRUSTED_FUGLE_HOST")
    if not SAFE_ENDPOINT.fullmatch(parsed.path):
        raise ValueError("UNSUPPORTED_FUGLE_ENDPOINT")
    params = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    if parameters:
        if not isinstance(parameters, dict):
            raise ValueError("INVALID_PARAMETERS")
        params.extend((str(k), str(v)) for k, v in parameters.items())
    if any(k not in ALLOWED_PARAMETERS or not v or len(v) > 64 for k, v in params):
        raise ValueError("INVALID_PARAMETER")
    values = {}
    for k, v in params:
        if k in values and values[k] != v:
            raise ValueError("CONFLICTING_PARAMETER")
        values[k] = v
    if "from" in values and "to" in values and values["from"] > values["to"]:
        raise ValueError("INVALID_DATE_RANGE")
    identity = {"provider": "fugle", "method": "GET",
                "endpoint": parsed.path.removeprefix("/marketdata/v1.0/stock/").lstrip("/"),
                "params": sorted(values.items())}
    raw = json.dumps(identity, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return "sky:fugle:endpoint:v1:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
