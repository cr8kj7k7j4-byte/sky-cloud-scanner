"""Read-only repository-wide market-data source inventory. No network calls or orders."""
from __future__ import annotations
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PATTERNS = {
    "MIS_QUOTE_ROUTE": re.compile(r"fetch_mis_quotes|MIS_URL|mis\.twse\.com\.tw|TWSE MIS|MIS fallback", re.I),
    "NON_FUGLE_PRICE_PROVIDER": re.compile(r"yfinance|yahooquery|query1\.finance\.yahoo|stooq|alpha.vantage|twelvedata", re.I),
    "FREE_MARKET_QUOTE_SOURCE": re.compile(r"tpex_mainboard_quotes|STOCK_DAY_ALL|openapi\.twse\.com\.tw", re.I),
    "FUGLE_SOURCE": re.compile(r"FUGLE_API_KEY|Fugle|SKY_FUGLE_ONLY_MARKETDATA", re.I),
}
TRACKED_EXTENSIONS = {".py", ".yml", ".yaml", ".md", ".json", ".toml", ".txt", ".sh", ".js", ".ts"}
SCOPES = ("src/", "research/", ".github/workflows/", "docs/", "tests/", "scan_requests/")

def audit(root: Path = Path(".")) -> dict:
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    tracked = [p.decode("utf-8") for p in proc.stdout.split(b"\x00") if p]
    findings = []
    totals = {name: 0 for name in PATTERNS}
    reviewed = 0
    for name in tracked:
        path = root / name
        if not path.is_file() or path.suffix.lower() not in TRACKED_EXTENSIONS:
            continue
        reviewed += 1
        if not name.startswith(SCOPES):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            findings.append({"path": name, "status": "UNREADABLE"})
            continue
        for n, line in enumerate(lines, 1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    totals[kind] += 1
                    findings.append({
                        "path": name, "line": n, "kind": kind,
                        "review": "VERIFY_NOT_PRICE_FEED" if kind == "FREE_MARKET_QUOTE_SOURCE"
                                  else "REVIEW_ACTUAL_RUNTIME_ROUTE" if kind != "FUGLE_SOURCE"
                                  else "SOURCE_REFERENCE_ONLY",
                    })
    return {
        "schema": "SKY_FUGLE_MARKETDATA_REPOSITORY_INVENTORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tracked_files": len(tracked),
        "text_files_examined": reviewed,
        "coverage": "all tracked text code, workflows, rules, docs and tests; not a dynamic runtime proof",
        "policy": "Whole-market paid Fugle TSE/OTC; single-stock verification Fugle; official universe/calendar identifiers allowed; no free price fallback",
        "counts": totals,
        "findings": findings,
        "production_verified": False,
        "note": "Keyword hits are leads, not confirmed violations. Review each actual execution path; historic documentation/tests are not automatically runtime defects.",
    }

def main() -> None:
    result = audit()
    out = Path("output/fugle_source_audit")
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "findings"}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
