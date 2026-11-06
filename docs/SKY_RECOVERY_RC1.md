# Sky Recovery RC1 — read-only candidate acceptance
Owner: W0/P0-G. Recovery branch: recovery/sky-core-acceptance-20261105.

This adds a deterministic **read-only** audit and 6 regression tests. A green workflow means the audit executed. It **never** authorizes trades, changes Alpha, bypasses quote-quality thresholds, or upgrades Production.

## Critical path / issue ownership
1. W3A/W3B: live TWSE/TPEx executed-price coverage and Fugle runner entitlements: #216, #217, #219.
2. W0/P0-G: authoritative current v1.4 forward strategy and decision-time provenance: #227. Do not revive archived P0-S.
3. W4/W6/P0-R: strategy outcomes, forward joins, execution attempts and real fill proof: #120 and #84.
4. Risk change collisions: review ONE of draft PR #253 / #265 for the two-consecutive-loss stop; real account-state source remains unproven.
5. Related draft optimizations #271/#272 and fail-closed PR #229 require separate CI, data-provenance and W0 reviews.

## Gate inputs
docs/SKY_EXTERNAL_LATEST_STATUS.json
docs/SKY_UNIFIED_LATEST_SYSTEM_HEALTH.json
docs/SKY_UNIFIED_LATEST_MODEL_VALIDATION.json

This auditor rejects missing/stale-status identifiers, unverified market-health verdict, missing formal strategy provenance, fewer than 200 *eligible strategy trades*, fewer than 20 true future days, fewer than 2 regimes, fewer than 95% complete eligible trade outcomes, unknown/excess symbol concentration, missing observed fills, and missing cost-adjusted expectancy.

IMPORTANT: this gate does not replace actual in-session quote validation, cost stress, capacity testing, OOS, W0/P0-G approval or live-broker reconciliation. Even a fully passing diagnostic only becomes READY_FOR_W0_P0G_REVIEW_ONLY.

## Usage
GitHub Actions > Sky Recovery Read-Only Acceptance > Run workflow.
Local: PYTHONPATH=. python -m unittest discover -s tests -p test_sky_recovery_gate.py -v
Local: PYTHONPATH=. python -m research.sky_recovery_gate
Artifact: sky-recovery-audit, file output/recovery/acceptance.json.

Do not automatically merge to main. No new schedule, no orders, no change to formal strategies.
