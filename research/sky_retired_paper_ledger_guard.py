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
    ".github/workflows/shadow-outcome-backfill.yml",
    ".github/workflows/shadow-promotion-dashboard.yml",
    "research/shadow_outcome_backfill.py",
    "research/shadow_promotion_dashboard.py",
    "tests/test_shadow_outcome_backfill.py",
    "tests/test_shadow_promotion_dashboard.py",
    "src/shadow_evidence.py",
    "tests/test_shadow_evidence.py",
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
    "research.shadow_outcome_backfill",
    "research.shadow_promotion_dashboard",
    "src.shadow_evidence",
    "research.sky_p0r_repair_status",
    "research.sky_paper_only_acceptance",
    "research.sky_paper_trade_trace",
)
IMPORT = re.compile(r"^\s*(?:from\s+((?:src\.paper_trading|research\.sky_(?:p0r_repair_status|paper_only_acceptance|paper_trade_trace)))\s+import\b|import\s+((?:src\.paper_trading|research\.sky_(?:p0r_repair_status|paper_only_acceptance|paper_trade_trace)))\b)", re.M)


def check(root=ROOT):
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    tracked = {p.decode("utf-8") for p in proc.stdout.split(b"\0") if p}
    violations = [{"path": p, "reason": "RETIRED_DEDICATED_COMPONENT"} for p in sorted(RETIRED_PATHS & tracked)]
    # Active runtime/configuration must not contain retired ledger switches or routes.
    runtime_tokens = (
        "PAPER_TRADING_MODE", "PAPER_GCS_BUCKET",
        "shadow-outcome-backfill.yml", "shadow-promotion-dashboard.yml",
        "from src.shadow_evidence import", "from research.shadow_outcome_backfill import",
        "research.sky_paper_only_acceptance", "research.sky_paper_trade_trace",
        "research.sky_p0r_repair_status", "sky-paper-only-acceptance.yml",
        "from .paper_trading import", "from src.paper_trading import",
        "import src.paper_trading",
    )
    for p in sorted(tracked):
        if p in RETIRED_PATHS or p in {
            "research/sky_retired_paper_ledger_guard.py",
            "tests/test_sky_retired_paper_ledger_guard.py",
            # Read-only inventory must list forbidden names as data, not runtime use.
            "research/sky_all_branches_retired_ledger_audit.py",
        }:
            continue
        if not (p.endswith((".py", ".yml", ".yaml", ".toml")) or p == ".env.example"):
            continue
        file = root / p
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for token in runtime_tokens:
            if token in source:
                violations.append({"path": p, "reason": "RETIRED_RUNTIME_REFERENCE", "token": token})
        if not p.endswith(".py"):
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
