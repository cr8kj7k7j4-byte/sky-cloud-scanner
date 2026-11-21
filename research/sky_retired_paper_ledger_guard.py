"""Fail-closed guard for the owner-retired simulated-trading ledger subsystem.

Narrowly prohibit only known dedicated acceptance/journal components and
their Python imports. Do not ban general research evidence, cost models,
real broker records, risk controls or the words 'paper'/'ledger'.
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED_PATHS = frozenset({
    ".github/workflows/sky-paper-only-acceptance.yml",
    "src/paper_trading.py",
    "tests/test_paper_trading.py",
    "research/sky_p0r_repair_status.py",
    "tests/test_sky_p0r_repair_status.py",
    "research/sky_paper_only_acceptance.py",
    "tests/test_sky_paper_only_acceptance.py",
    "research/sky_paper_trade_trace.py",
    "tests/test_sky_paper_trade_trace.py",
})
RETIRED_MODULES = (
    "src.paper_trading",
    "research.sky_p0r_repair_status",
    "research.sky_paper_only_acceptance",
    "research.sky_paper_trade_trace",
)
IMPORT = re.compile(r"^\\s*(?:from\\s+((?:src\\.paper_trading|research\\.sky_(?:p0r_repair_status|paper_only_acceptance|paper_trade_trace)))\\s+import\\b|import\\s+((?:src\\.paper_trading|research\\.sky_(?:p0r_repair_status|paper_only_acceptance|paper_trade_trace)))\\b)", re.M)


def check(root=ROOT):
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    tracked = {p.decode("utf-8") for p in proc.stdout.split(b"\0") if p}
    violations = [{"path": p, "reason": "RETIRED_DEDICATED_COMPONENT"} for p in sorted(RETIRED_PATHS & tracked)]
    for p in sorted(tracked):
        if not p.endswith(".py") or p in RETIRED_PATHS:
            continue
        file = root / p
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in IMPORT.finditer(source):
            violations.append({"path": p, "reason": "RETIRED_MODULE_IMPORT", "module": match.group(1) or match.group(2)})
    return {"schema": "SKY_RETIRED_PAPER_LEDGER_GUARD_V1",
            "passed": not violations, "violations": violations,
            "production_eligible": False, "automatic_order": False}


if __name__ == "__main__":
    report = check()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
