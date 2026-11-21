# Sky 503 retired-ledger branch review — 2026-11-22

## Evidence and scope
- Baseline full branch audit: [workflow 44925470122](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44925470122), 633 scanned / 503 affected, [artifact 14714963178](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44925470122/artifacts/14714963178).
- Baseline classification: 493 affected branches HOLD due to commits ahead of main; 10 review-delete candidates (0 ahead); all deletions blocked.
- Current main at comparison: `638c16ed0d88b9b02654590fd244151e63e6cd4a`. All ten candidates rechecked against this SHA through GitHub compare: status **behind**, ahead=0.
- At review, open PRs were #626 and #627, neither head from the ten candidates. Tracked-main textual-branch-reference scan did not flag these ten.
- **No branch deletions, no Production modification, no automatic model promotion.**

## Ten candidate branches rechecked against main

| Candidate branch | Ahead / behind | Gate 1 | Gate 2 and final disposition |
|---|---:|---|---|
| `engineering/w3a-fugle-expanded-free-probe-v2-20261026` | 0 / 892 | Pass: ancestor of main | External/other-branch dependencies unverified; HOLD |
| `feat/position-table-v14-20261027` | 0 / 857 | Pass | HOLD |
| `fix/intraday-coverage-gate-20261103` | 0 / 803 | Pass | HOLD |
| `fix/reregister-intraday-schedule-20261103` | 0 / 801 | Pass | HOLD |
| `fix/three-model-evening-schedule-health-20261108` | 0 / 464 | Pass | HOLD |
| `fix/three-model-weekend-followup-20261108` | 0 / 469 | Pass | HOLD |
| `research/three-model-daily-ledger-and-followup-20261108` | 0 / 473 | Pass | HOLD |
| `research/w0-redis-cas-shared-runner-20261111` | 0 / 81 | Pass | HOLD |
| `research/w0-repair-progress-existing-watchdog-20261110` | 0 / 88 | Pass | HOLD |
| `w3b/telegram-smoke-diagnostic-20261026` | 0 / 918 | Pass | HOLD |

## Research value triage for unique-commit branches

There are **493 affected branches with commits not in main history**. This count does not imply 493 unique valuable features: squashed/cherry-picked semantic equivalents must be checked against main before deciding.

Priority **P0 — verify, preserve useful changes but do NOT merge whole branches**:
- `research/sky-536-531-guard-readback` (169 ahead): mobile result readback and paid API dedup; modified scan/bridge workflows contain retired module references.
- `research/w0-fugle-api-dedup-guard-20261111` (153): paid API concurrency/quote guard; requires real cross-workflow evidence.
- `research/fugle-snapshot-diagnostics-20261110` (100): snapshot integrity and artifact readback.
- `research/sky-mobile-paper-integration` (299) and `research/sky-paper-snapshot-session-gate` (257): broad mobile/data integration mixed with retired paper/shadow paths. **Quarantine retired pieces.**
- `fix/sky-alert-freshness-reader-20261111` (51): stale-data guard and warning reader.

Priority **P1 — historical-data integrity and independent risk controls**:
- `engineering/w3-swing-pit-price-20261025` (52): swing PIT price sourcing and coverage evidence.
- `w3a/intraday-pit-convergence` (43): point-in-time data semantics and benchmark audit.
- `feature/historical-universe-audit` (43): historical universe/listing/delisting evidence.
- `research/three-model-evidence-gate-20261108` (43): model evidence verification.
- `research/p0r-failclosed-guards-20261110` (90) and `w6/risk-ledger-fail-closed-20261108` (31): separate real risk protection from retired simulation-related modules.

Priority **quarantine retired-paper evidence**:
- `research/sky-market-paper-evidence-20261121` (95): contains simulator/order/replay/ledger components that must not return. Reuse only independently verified non-ledger risk guards.
- Other paper/shadow/ledger-labelled branches must be checked for actual paths and behavioral semantics, not solely name.

Remaining unique-commit branches: retained for file-by-file and squash-equivalence review; no deletion or merge approval implied.

## Gates and next acceptance
1. Commit divergence: 10 pass, 493 require independent research value review.
2. Dependencies: open PR/main tracked-text partially checked. Other branches, external automation, tags, deployed endpoints, workflow secrets and schedule references **not fully verified**.
3. Preserve: only carry forward independent, non-retired functionality by discrete reviewed PR with CI, artifact and governance; no wholesale merges.
4. Delete: **0 authorized**, no branch deletion. Recheck exact SHAs and live dependencies before any batch deletion.

**Status: HOLD (not final cleanup acceptance).**
