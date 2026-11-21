"""Fail-closed regression guard for retired #508 simulated trade ledger.

Checks tracked source and workflow files, not historical Git commits or documents.
This guard never accesses market APIs or order endpoints.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RETIRED = {
    ".github/workflows/sky-paper-only-acceptance.yml",
    "research/sky_paper_only_acceptance.py",
    "research/sky_paper_trade_trace.py",
    "tests/test_sky_paper_only_acceptance.py",
    "tests/test_sky_paper_trade_trace.py",
}
SOURCE_SUFFIXES = {".py", ".yml", ".yaml"}
FORBIDDEN = (
    "sky_paper_only_acceptance",
    "sky_paper_trade_trace",
    "paper_fill_count",
    "paper_events_produced",
    "BARS_VERIFIED_PRECOMMITTED_SIGNAL_MISSING",
)

def audit():
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    )
    tracked = {p.decode("utf-8") for p in result.stdout.split(b"\0") if p}
    problems = ["RETIRED_FILE:" + p for p in sorted(RETIRED & tracked)]
    for name in sorted(tracked):
        path = ROOT / name
        if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
            continue
        if name == "research/sky_retired_ledger_guard.py":
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for marker in FORBIDDEN:
            if marker in data:
                problems.append(f"RETIRED_DEPENDENCY:{name}:{marker}")
    return problems

if __name__ == "__main__":
    errors = audit()
    for error in errors:
        print(error)
    if errors:
        raise SystemExit("RETIRED_LEDGER_DEPENDENCIES_REMAIN")
    print("RETIRED_LEDGER_GUARD_PASS")
