#!/usr/bin/env python3
"""Read-only inventory of retired simulated-ledger paths in all remote branch tips."""
import json
import re
import tempfile
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

def classify_branch(branch, ahead, refs, matches, unique_paths):
    """Never declare deletion safe based only on a static inventory."""
    if branch == "main" or branch.startswith(("release/", "production/", "prod/")):
        return "PROTECT", "default_or_release_branch"
    if ahead is None:
        return "HOLD", "commit_comparison_failed"
    if ahead > 0:
        return "HOLD", "unique_commits_require_research_review"
    if refs:
        return "HOLD", "tracked_reference_requires_dependency_review"
    if unique_paths:
        return "HOLD", "unique_paths_require_preservation"
    if matches:
        return "REVIEW_DELETE_CANDIDATE", "no_unique_commits_or_tracked_references; external_deps_and_owner_approval_pending"
    return "NO_RETIRED_PATH", "no_exact_retired_path_found; not_a_deletion_approval"


def main():
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines()
    refs = [r for r in refs if r.startswith("origin/") and r != "origin/HEAD"]
    if not refs:
        raise SystemExit("No remote branches enumerated: fail closed")
    main_ref = "origin/main"
    if main_ref not in refs:
        raise SystemExit("origin/main unavailable: fail closed")

    # Search tracked source, documentation, and workflows on main for literal
    # branch-name references in one batched git grep. External GitHub schedules,
    # secrets, tags, open PRs, and dependent branches still require review.
    branches = [r.removeprefix("origin/") for r in sorted(refs)]
    reference_map = {b: [] for b in branches}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as f:
        f.write("\n".join(branches) + "\n")
        f.flush()
        proc = subprocess.run(
            ["git", "grep", "-I", "-n", "-F", "-f", f.name, "origin/main",
             "--", ".github/workflows", "docs", "research", "src", "README.md"],
            text=True, capture_output=True,
        )
        if proc.returncode not in (0, 1):
            raise SystemExit("Reference search failed: " + proc.stderr)
        for line in proc.stdout.splitlines():
            for b in branches:
                if b in line:
                    reference_map[b].append(line[:350])

    rows = []
    for ref in sorted(refs):
        branch = ref.removeprefix("origin/")
        sha = git("rev-parse", ref)
        paths = set(git("ls-tree", "-r", "--name-only", sha).splitlines())
        matches = sorted(paths.intersection(RETIRED))
        try:
            left, right = map(int, git("rev-list", "--left-right", "--count",
                                       main_ref + "..." + ref).split())
            behind, ahead = left, right
            # This diff is a *candidate* change inventory, not a guarantee of
            # semantic uniqueness after squash/cherry-pick.
            changed = git("diff", "--name-only", main_ref + "..." + ref).splitlines()
            unique_paths = sorted(p for p in changed if p not in RETIRED)
        except (subprocess.CalledProcessError, ValueError):
            behind, ahead, unique_paths = None, None, []
        references = reference_map[branch]
        status, reason = classify_branch(branch, ahead, references, matches, unique_paths)
        rows.append({
            "branch": branch, "sha": sha, "retired_paths": matches,
            "retired_path_count": len(matches),
            "ahead_main": ahead, "behind_main": behind,
            "non_retired_changed_paths": unique_paths[:100],
            "non_retired_changed_paths_truncated": len(unique_paths) > 100,
            "tracked_main_references": references[:20],
            "tracked_main_references_truncated": len(references) > 20,
            "decision": status, "reason": reason,
            "gate_1_commit_diff": "PASS_NO_UNIQUE_COMMITS" if ahead == 0 else "HOLD_REVIEW",
            "gate_2_dependency": "HOLD_EXTERNAL_AND_PR_CHECK_REQUIRED",
            "gate_3_preservation": "HOLD_UNTIL_REVIEWED" if ahead else "NOT_REQUIRED_FOR_IDENTICAL_HISTORY",
            "gate_4_cleanup": "BLOCKED_OWNER_REVIEW_REQUIRED",
        })
    from collections import Counter
    counts = dict(Counter(r["decision"] for r in rows))
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "remote branch HEAD trees; commit divergence and tracked main text references",
        "branch_count": len(rows),
        "affected_count": sum(bool(r["retired_paths"]) for r in rows),
        "decision_counts": counts, "branches": rows,
        "limitations": [
            "No source-content/import scan or full history purge",
            "No proof of external workflow/schedule/branch/PR dependencies",
            "git rev-list may count already squash-merged equivalent changes",
            "No preservation/merge or automatic deletion",
            "REVIEW_DELETE_CANDIDATE is not permission to delete",
        ],
    }
    Path("retired-ledger-all-branches.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Four-gate retired ledger branch audit", "",
        f"Branches checked: {len(rows)}",
        f"Branches with retired exact paths: {result['affected_count']}",
        f"Decisions: {counts}", "",
        "| Branch | Retired paths | Ahead | Behind | Decision | Reason |",
        "|---|---:|---:|---:|---|---|",
    ]
    for r in rows:
        if r["retired_path_count"]:
            lines.append(f'| `{r["branch"]}` | {r["retired_path_count"]} | '
                         f'{r["ahead_main"]} | {r["behind_main"]} | '
                         f'{r["decision"]} | {r["reason"]} |')
    lines += [
        "", "Gate 1: git divergence plus changed-path inventory.",
        "Gate 2: main tracked reference scan; external dependencies remain unverified.",
        "Gate 3: unmerged candidate work stays HOLD pending preservation and tests.",
        "Gate 4: no deletion executed or authorized; owner must review evidence.",
    ]
    report = "\n".join(lines) + "\n"
    Path("retired-ledger-all-branches.md").write_text(report, encoding="utf-8")
    print("\n".join(lines[:7]))
    if counts.get("PROTECT", 0) < 1:
        raise SystemExit("Default branch not protected: fail closed")


if __name__ == "__main__":
    main()
