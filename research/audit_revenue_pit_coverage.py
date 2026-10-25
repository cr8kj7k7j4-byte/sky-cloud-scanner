from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def load_revenue_rows(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("monthly_revenue.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    symbol = str(row.get("symbol") or "").strip()
                    year = int(row.get("year"))
                    month = int(row.get("month"))
                    market = str(row.get("market") or "").strip()
                except Exception:
                    continue
                if not symbol or month < 1 or month > 12:
                    continue
                rows.append({
                    "symbol": symbol,
                    "year": year,
                    "month": month,
                    "market": market,
                })
    return rows


def load_pit_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        if item.get("filing_timestamp_source") != "MOPS_OFFICIAL":
            continue
        if not item.get("point_in_time_verified"):
            continue
        if not item.get("filing_published_at"):
            continue
        rows.append(item)
    return rows


def build_coverage_report(
    revenue_rows: list[dict],
    pit_rows: list[dict],
    *,
    min_coverage_pct: float = 100.0,
) -> dict:
    expected = {
        (
            str(r["symbol"]),
            int(r["year"]),
            int(r["month"]),
            str(r.get("market") or ""),
        )
        for r in revenue_rows
    }

    pit_key_loose = {
        (
            str(r.get("symbol") or ""),
            int(r.get("revenue_year")),
            int(r.get("revenue_month")),
        )
        for r in pit_rows
        if r.get("symbol") and r.get("revenue_year") and r.get("revenue_month")
    }

    covered = {
        key
        for key in expected
        if (key[0], key[1], key[2]) in pit_key_loose
    }
    missing = expected - covered

    def pct(a, b):
        return round((a / b * 100.0), 4) if b else 0.0

    by_year = defaultdict(lambda: {"expected": 0, "covered": 0})
    by_market = defaultdict(lambda: {"expected": 0, "covered": 0})
    for key in expected:
        symbol, year, month, market = key
        by_year[str(year)]["expected"] += 1
        by_market[market]["expected"] += 1
        if key in covered:
            by_year[str(year)]["covered"] += 1
            by_market[market]["covered"] += 1

    for bucket in (by_year, by_market):
        for stats in bucket.values():
            stats["coverage_pct"] = pct(stats["covered"], stats["expected"])

    coverage_pct = pct(len(covered), len(expected))
    gate_pass = bool(expected) and coverage_pct >= float(min_coverage_pct)

    return {
        "schema_version": "1.0",
        "expected_company_months": len(expected),
        "covered_company_months": len(covered),
        "missing_company_months": len(missing),
        "coverage_pct": coverage_pct,
        "min_coverage_pct": float(min_coverage_pct),
        "historical_pit_gate_pass": gate_pass,
        "promotion_allowed": gate_pass,
        "status": "PIT_COVERAGE_PASS" if gate_pass else "PRE_PIT_CANDIDATE",
        "by_year": dict(sorted(by_year.items())),
        "by_market": dict(sorted(by_market.items())),
        "missing_sample": [
            {
                "symbol": s,
                "year": y,
                "month": m,
                "market": market,
            }
            for s, y, m, market in sorted(missing)[:200]
        ],
        "governance": {
            "proxy_dates_count_as_covered": False,
            "official_source_required": "MOPS_OFFICIAL",
            "verified_timestamp_required": True,
            "rule": (
                "Historical PIT coverage must pass before revenue candidates "
                "can leave PRE_PIT_CANDIDATE."
            ),
        },
    }


def write_markdown(report: dict, path: Path):
    lines = [
        "# Revenue Historical PIT Coverage Audit",
        "",
        f"- Expected company-months: {report['expected_company_months']:,}",
        f"- Covered company-months: {report['covered_company_months']:,}",
        f"- Missing company-months: {report['missing_company_months']:,}",
        f"- Coverage: {report['coverage_pct']:.4f}%",
        f"- Required: {report['min_coverage_pct']:.4f}%",
        f"- Gate: {'PASS' if report['historical_pit_gate_pass'] else 'FAIL'}",
        f"- Status: {report['status']}",
        "",
        "## By year",
        "",
        "| Year | Expected | Covered | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for year, x in report["by_year"].items():
        lines.append(
            f"| {year} | {x['expected']:,} | {x['covered']:,} | "
            f"{x['coverage_pct']:.4f}% |"
        )
    lines += [
        "",
        "## Governance",
        "",
        "- Statutory-deadline proxy dates do not count as covered.",
        "- Only official, verified MOPS publication timestamps count.",
        "- Coverage failure blocks Promotion; it does not invalidate the revenue values themselves.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revenue-root", required=True)
    ap.add_argument(
        "--pit-ledger",
        default="data/revenue_pit/mops_revenue_filing_times.jsonl",
    )
    ap.add_argument("--min-coverage-pct", type=float, default=100.0)
    ap.add_argument("--out", default="output/revenue_pit_coverage")
    args = ap.parse_args()

    revenue = load_revenue_rows(Path(args.revenue_root))
    pit = load_pit_rows(Path(args.pit_ledger))
    report = build_coverage_report(
        revenue,
        pit,
        min_coverage_pct=args.min_coverage_pct,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(report, out / "coverage.md")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
