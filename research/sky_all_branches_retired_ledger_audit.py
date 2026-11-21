#!/usr/bin/env python3
"""Read-only inventory of retired simulated-ledger paths in all remote branch tips."""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RETIRED = (
    ".github/workflows/sky-paper-only-acceptance.yml",
    ".github/workflows/shadow-outcome-backfill.yml",
    ".github/workflows/shadow-promotion-dashboard.yml",
    "src/paper_trading.py",
    "src/shadow_evidence.py",
    "research/shadow_outcome_backfill.py",
    "research/shadow_promotion_dashboard.py",
    "research/sky_p0r_repair_status.py",
    "research/sky_paper_only_acceptance.py",
    "research/sky_paper_trade_trace.py",
    "tests/test_shadow_outcome_backfill.py",
    "tests/test_shadow_promotion_dashboard.py",
    "tests/test_shadow_evidence.py",
    "tests/test_paper_trading.py",
    "tests/test_sky_p0r_repair_status.py",
    "tests/test_sky_paper_only_acceptance.py",
    "tests/test_sky_paper_trade_trace.py",
)

def git(*args):
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.PIPE).strip()

def main():
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines()
    refs = [r for r in refs if r.startswith("origin/") and r != "origin/HEAD"]
    rows = []
    for ref in sorted(refs):
        sha = git("rev-parse", ref)
        paths = set(git("ls-tree", "-r", "--name-only", sha).splitlines())
        matches = sorted(paths.intersection(RETIRED))
        rows.append({"branch": ref.removeprefix("origin/"), "sha": sha, "retired_paths": matches, "retired_path_count": len(matches)})
    result = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "remote branch HEAD trees, exact retired paths only", "branch_count": len(rows), "affected_count": sum(bool(r["retired_paths"]) for r in rows), "branches": rows, "limitations": ["No source-content/import scan", "No historical commit-object purge", "No automatic branch deletion", "No claim that unmatched branches have zero retired references"]}
    Path("retired-ledger-all-branches.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Retired ledger branch-tip audit", "", f"Branches checked: {len(rows)}", f"Branches with retired exact paths: {result['affected_count']}", "", "| Branch | SHA | Retired paths |", "|---|---|---:|"]
    lines.extend(f"| `{r['branch']}` | `{r['sha'][:12]}` | {r['retired_path_count']} |" for r in rows if r["retired_path_count"])
    lines.extend(["", "Scope: branch-tip tracked paths, not full file-content inspection or Git history. No branches deleted."])
    Path("retired-ledger-all-branches.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if not rows:
        raise SystemExit("No remote branches enumerated: fail closed")

if __name__ == "__main__":
    main()
