from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
MOPS_API = "https://mops.twse.com.tw/mops/api/home_page/t51sb10"
MOPS_SOURCE_PAGE = "https://mops.twse.com.tw/mops/web/t51sb10"

MARKETS = {
    "sii": "TWSE",
    "otc": "TPEx",
    "rotc": "EMERGING",
    "pub": "PUBLIC",
}

SUBJECT_RE = re.compile(r"(?P<roc_year>\d{3})(?P<month>\d{2})-營業收入資訊")
SYMBOL_RE = re.compile(r"^\d{4,6}$")
TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")
ROC_DATETIME_RE = re.compile(
    r"^(?P<y>\d{3})/(?P<m>\d{1,2})/(?P<d>\d{1,2})\s+"
    r"(?P<h>(?:[01]?\d|2[0-3])):(?P<mi>[0-5]\d)(?::(?P<s>[0-5]\d))?$"
)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(value) -> str:
    s = html.unescape(str(value or ""))
    s = TAG_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def roc_datetime_to_iso(value: str) -> str:
    m = ROC_DATETIME_RE.fullmatch(_clean(value))
    if not m:
        raise ValueError(f"Invalid ROC datetime: {value!r}")
    year = int(m.group("y")) + 1911
    dt = datetime(
        year,
        int(m.group("m")),
        int(m.group("d")),
        int(m.group("h")),
        int(m.group("mi")),
        int(m.group("s") or 0),
        tzinfo=TZ,
    )
    return dt.isoformat()


def _server_date(payload: dict) -> str:
    dt = roc_datetime_to_iso(str(payload.get("datetime") or ""))
    return dt[:10]


def fetch_json_post(url: str, payload: dict, timeout: int = 20) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0 SkyResearchBot/1.0",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    data = json.loads(raw.decode("utf-8", errors="strict"))
    if not isinstance(data, dict):
        raise ValueError("MOPS API response must be an object")
    return data


def fetch_market(market_kind: str, count: int = 500) -> dict:
    if market_kind not in MARKETS:
        raise ValueError(f"Unsupported marketKind: {market_kind}")
    return fetch_json_post(
        MOPS_API,
        {"count": int(count), "marketKind": market_kind},
    )


def _iter_candidate_rows(value):
    """
    Yield row-like containers from unknown-but-JSON MOPS response structures.

    The API is official but its front-end response schema is not a documented
    public contract. This walker deliberately accepts dict/list row shapes while
    the semantic parser below still requires symbol + revenue subject + publish
    time before a PIT record can be emitted.
    """
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list, tuple)):
                yield from _iter_candidate_rows(child)
    elif isinstance(value, (list, tuple)):
        # A primitive list can itself be a table row.
        if value and all(not isinstance(x, (dict, list, tuple)) for x in value):
            yield list(value)
        for child in value:
            if isinstance(child, (dict, list, tuple)):
                yield from _iter_candidate_rows(child)


def _primitive_strings(row) -> list[str]:
    if isinstance(row, dict):
        values = row.values()
    elif isinstance(row, (list, tuple)):
        values = row
    else:
        return []
    return [_clean(x) for x in values if not isinstance(x, (dict, list, tuple))]


def _pick_name(strings: list[str], symbol: str, publish_text: str, subject: str) -> str | None:
    for i, value in enumerate(strings):
        if value == symbol and i + 1 < len(strings):
            candidate = strings[i + 1]
            if (
                candidate
                and candidate != publish_text
                and candidate != subject
                and not SYMBOL_RE.fullmatch(candidate)
                and not TIME_RE.fullmatch(candidate)
                and not ROC_DATETIME_RE.fullmatch(candidate)
            ):
                return candidate
    return None


def _resolve_publish_datetime(publish_text: str, server_date: str) -> str:
    if ROC_DATETIME_RE.fullmatch(publish_text):
        return roc_datetime_to_iso(publish_text)
    if TIME_RE.fullmatch(publish_text):
        return datetime.fromisoformat(
            f"{server_date}T{publish_text}:00"
        ).replace(tzinfo=TZ).isoformat()
    raise ValueError(f"Unusable publish time: {publish_text!r}")


def parse_api_response(
    payload: dict,
    *,
    market_kind: str,
    observed_at: str | None = None,
) -> list[dict]:
    if market_kind not in MARKETS:
        raise ValueError(f"Unsupported marketKind: {market_kind}")

    code = payload.get("code")
    if code != 200:
        raise ValueError(
            f"MOPS API rejected marketKind={market_kind}: "
            f"code={code} message={payload.get('message')}"
        )

    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("MOPS API result is missing or malformed")

    data = result.get("data")
    if data in (None, []):
        return []

    server_date = _server_date(payload)
    observed_at = observed_at or datetime.now(TZ).isoformat()

    out = []
    seen = set()
    for row in _iter_candidate_rows(data):
        strings = _primitive_strings(row)
        if not strings:
            continue

        subject = next((x for x in strings if SUBJECT_RE.search(x)), None)
        symbol = next((x for x in strings if SYMBOL_RE.fullmatch(x)), None)
        publish_text = next(
            (
                x for x in strings
                if TIME_RE.fullmatch(x) or ROC_DATETIME_RE.fullmatch(x)
            ),
            None,
        )
        if not subject or not symbol or not publish_text:
            continue

        sm = SUBJECT_RE.search(subject)
        filing_published_at = _resolve_publish_datetime(
            publish_text,
            server_date,
        )
        key = (
            symbol,
            int(sm.group("roc_year")) + 1911,
            int(sm.group("month")),
            filing_published_at,
        )
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "schema_version": "1.0",
            "symbol": symbol,
            "name": _pick_name(strings, symbol, publish_text, subject),
            "market": MARKETS[market_kind],
            "market_kind": market_kind,
            "revenue_year": key[1],
            "revenue_month": key[2],
            "filing_published_at": filing_published_at,
            "filing_timestamp_source": "MOPS_OFFICIAL",
            "observed_at": observed_at,
            "source_url": MOPS_SOURCE_PAGE,
            "source_api": MOPS_API,
            "source_subject": subject,
            "point_in_time_verified": True,
        })

    return out


def collect_all_markets(count: int = 500) -> tuple[list[dict], dict]:
    observed_at = datetime.now(TZ).isoformat()
    all_rows = []
    raw = {}
    for market_kind in MARKETS:
        payload = fetch_market(market_kind, count=count)
        raw[market_kind] = payload
        all_rows.extend(
            parse_api_response(
                payload,
                market_kind=market_kind,
                observed_at=observed_at,
            )
        )

    dedup = {}
    for row in all_rows:
        key = (
            row["symbol"],
            row["revenue_year"],
            row["revenue_month"],
            row["filing_published_at"],
        )
        dedup[key] = row
    return list(dedup.values()), raw


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except json.JSONDecodeError:
            continue
    return rows


def append_dedup_jsonl(path: Path, rows: list[dict]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_jsonl(path)
    keys = {
        (
            str(x.get("symbol")),
            x.get("revenue_year"),
            x.get("revenue_month"),
            x.get("filing_published_at"),
        )
        for x in existing
    }
    new_rows = []
    for x in rows:
        key = (
            str(x.get("symbol")),
            x.get("revenue_year"),
            x.get("revenue_month"),
            x.get("filing_published_at"),
        )
        if key not in keys:
            keys.add(key)
            new_rows.append(x)

    merged = existing + new_rows
    text = "".join(
        json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
        for x in merged
    )
    path.write_text(text, encoding="utf-8")
    return {
        "existing": len(existing),
        "added": len(new_rows),
        "total": len(merged),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default="data/revenue_pit/mops_revenue_filing_times.jsonl",
    )
    ap.add_argument(
        "--snapshot",
        default="output/mops_revenue_pit_snapshot.json",
    )
    ap.add_argument("--count", type=int, default=500)
    args = ap.parse_args()

    observed_at = datetime.now(TZ).isoformat()
    rows, raw = collect_all_markets(count=args.count)

    snapshot = Path(args.snapshot)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source": "MOPS_OFFICIAL",
                "source_url": MOPS_SOURCE_PAGE,
                "source_api": MOPS_API,
                "observed_at": observed_at,
                "records": rows,
                "raw_market_status": {
                    k: {
                        "code": v.get("code"),
                        "message": v.get("message"),
                        "datetime": v.get("datetime"),
                        "rows": len((v.get("result") or {}).get("data") or []),
                    }
                    for k, v in raw.items()
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    stats = append_dedup_jsonl(Path(args.out), rows)
    print(
        json.dumps(
            {
                "observed_at": observed_at,
                "parsed_records": len(rows),
                "markets": list(MARKETS),
                **stats,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
