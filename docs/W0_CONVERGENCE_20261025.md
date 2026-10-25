# W0｜Sky 總控收斂紀錄 — 2026-10-25

> W0 is the only master-control workstream. GitHub is the Single Source of Truth. This document records convergence; it does not create trading-profitability claims.

## 1. Production baseline
- Sky V2.1 Baseline — FROZEN
- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP — ACTIVE
- Sky Swing V1.0 — ACTIVE
- No Production version change in this convergence.

## 2. Champion / Challenger
### Champion
- Day Trading v1.4 / P0-C MVP
- Swing V1.0

### Challengers / blocked research
- Swing 5D 3-factor top-decile candidate — HOLD
- Revenue MoM 5D — PRE_PIT_CANDIDATE / HOLD
- Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE / HOLD
- Revenue YoY 5D — HOLD_CONCENTRATION_FAIL
- Revenue YoY 20D — HOLD_CONCENTRATION_FAIL

### Promotion
- PROMOTE_CANDIDATE: NONE

## 3. W1–W5 convergence
| Workstream | Formal W0 status | Next permitted action |
|---|---|---|
| W1 Swing | HOLD | Only pre-registered canonical-PIT replay / validation; no duplicate rerun of current-universe artifact as new evidence |
| W2 Intraday | FREEZE / DISCIPLINE | Keep rejected families frozen; only structurally distinct preregistered research may enter |
| W3 Data & Engineering | ACTIVE PRIORITY | PIT/data quality, official TPEx chain, feature schema/DQ, alerts, runtime/E2E, rollback |
| W4 Shadow/Paper | WAITING_FOR_SUFFICIENCY | Prospectively accumulate canonical records/outcomes and evaluate sufficiency gates |
| W5 Candidate Lab | INTAKE ONLY | No active VNext alpha authorization; screen for duplicate/low-value ideas first |

## 4. W1 decision rationale
Existing Swing research is not eligible for promotion because:
1. Current 100-symbol artifact uses today's/current listing universe backward and therefore fails artifact-level PIT / survivorship validation.
2. 5D walk-forward evidence is mixed.
3. 0.65% cost-stress stability fails consistently.
4. Portfolio overlap, correlation, sector concentration, capacity/liquidity, heat and full ablation are incomplete.
5. 2026 data has already been observed and is not fresh untouched OOS.
6. Shadow/Paper evidence is not sufficient.

Result: HOLD. Do not select 10D/15D/20D after seeing results and call it a new Champion.

## 5. W4 sufficiency gate
Before any Small Live consideration:
- >= 200 evaluable samples
- >= 20 trading days
- >= 2 market regimes
- outcome completeness >= 95%
- single-symbol share <= 20%
- after-cost portfolio evidence evaluable
- capacity/liquidity evidence evaluable
- P0-R risk gate pass
- P0-G review pass

Counterfactual outcomes are not real fills or realized P&L.

## 6. Freeze enforcement
REJECTED / ARCHIVED_NO_RETUNE families remain frozen. They may not be revived by:
- threshold tuning
- Top-N changes
- indicator-period changes
- feature-weight changes
- stop/target tweaks

Reopening requires a structural change in data, target/label, horizon, or execution architecture and a new preregistration.

## 7. Execution priority
1. Evidence completion
2. Shadow/Paper accumulation
3. Portfolio/Risk validation
4. Production hardening
5. Only then new alpha research

## 8. Stop conditions requiring user intervention
W0 continues autonomously except when:
1. New external account/API credentials are required.
2. Real capital or irreversible risk is involved.
3. User-specific 1R / max position must be set.
4. Critical external data is unavailable.
5. Manual ChatGPT window creation/switching is required.

## 9. Current W0 decision
- Production change: NO
- Promotion: NONE
- New module creation: NO
- Duplicate research rerun: NO
- User intervention required now: NO
