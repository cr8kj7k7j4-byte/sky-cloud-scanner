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
MOPS_HOME = "https://mops.twse.com.tw/"
SUBJECT_RE = re.compile(r"(?P<roc_year>\d{3})(?P<month>\d{2})-營業收入資訊")
DATE_RE = re.compile(r"最後更新時間\s*(?P<roc_date>\d{3}/\d{1,2}/\d{1,2})")
TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")
SYMBOL_RE = re.compile(r"^\d{4,6}$")
TAG_RE = re.compile(r"<[^>]+>")
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.I | re.S)


def _text(fragment: str) -> str:
    s = TAG_RE.sub(" ", fragment)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_homepage(timeout: int = 20) -> str:
    req = urllib.request.Request(
        MOPS_HOME,
        headers={
            "User-Agent": "Mozilla/5.0 SkyResearchBot/1.0",
            "Accept-Language": "zh-TW,zh;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="ignore")


def roc_date_to_iso_date(roc_date: str) -> str:
    ry, month, day = [int(x) for x in roc_date.split("/")]
    year = ry + 1911
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_revenue_filings(page_html: str, observed_at: str | None = None) -> list[dict]:
    plain = _text(page_html)
    date_match = DATE_RE.search(plain)
    if not date_match:
        raise ValueError("MOPS page date context not found; PIT timestamp cannot be resolved safely")

    iso_date = roc_date_to_iso_date(date_match.group("roc_date"))
    observed_at = observed_at or datetime.now(TZ).isoformat()

    out = []
    seen = set()
    for row_html in ROW_RE.findall(page_html):
        cells = [_text(x) for x in CELL_RE.findall(row_html)]
        if not cells:
            continue

        subject = next((x for x in cells if SUBJECT_RE.search(x)), None)
        if subject is None:
            continue

        subject_match = SUBJECT_RE.search(subject)
        symbol = next((x for x in cells if SYMBOL_RE.fullmatch(x)), None)
        published_time = next((x for x in cells if TIME_RE.fullmatch(x)), None)
        if not symbol or not published_time:
            continue

        name = None
        try:
            idx = cells.index(symbol)
            if idx + 1 < len(cells):
                candidate = cells[idx + 1]
                if candidate != published_time and not SUBJECT_RE.search(candidate):
                    name = candidate
        except ValueError:
            pass

        filing_dt = datetime.fromisoformat(
            f"{iso_date}T{published_time}:00"
        ).replace(tzinfo=TZ)

        revenue_year = int(subject_match.group("roc_year")) + 1911
        revenue_month = int(subject_match.group("month"))
        key = (symbol, revenue_year, revenue_month, filing_dt.isoformat())
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "schema_version": "1.0",
            "symbol": symbol,
            "name": name,
            "revenue_year": revenue_year,
            "revenue_month": revenue_month,
            "filing_published_at": filing_dt.isoformat(),
            "filing_timestamp_source": "MOPS_OFFICIAL",
            "observed_at": observed_at,
            "source_url": MOPS_HOME,
            "source_subject": subject,
            "point_in_time_verified": True,
        })

    return out


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
    text = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in merged)
    path.write_text(text, encoding="utf-8")
    return {
        "existing": len(existing),
        "added": len(new_rows),
        "total": len(merged),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/revenue_pit/mops_revenue_filing_times.jsonl")
    ap.add_argument("--snapshot", default="output/mops_revenue_pit_snapshot.json")
    args = ap.parse_args()

    page = fetch_homepage()
    raw_path = Path("output/mops_home_raw.html")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(page, encoding="utf-8")
    observed_at = datetime.now(TZ).isoformat()
    rows = parse_revenue_filings(page, observed_at=observed_at)

    snapshot = Path(args.snapshot)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        json.dumps({
            "schema_version": "1.0",
            "source": "MOPS_OFFICIAL",
            "source_url": MOPS_HOME,
            "observed_at": observed_at,
            "records": rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    stats = append_dedup_jsonl(Path(args.out), rows)
    print(json.dumps({
        "observed_at": observed_at,
        "parsed_records": len(rows),
        **stats,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
