# Sky GitHub Actions Scheduling Map — 2026-10-26

> Purpose: move Sky operational scheduling away from ChatGPT Automations and make GitHub Actions the primary scheduler for the governed research/evidence pipeline.

## Canonical weekday schedule (Asia/Taipei)

| Time | Workflow | Purpose | Production impact |
|---|---|---|---|
| 09:05 | `.github/workflows/scan.yml` | Sky intraday scan / Shadow snapshot | NONE |
| 09:15 | `.github/workflows/scan.yml` | Sky intraday scan / Shadow snapshot | NONE |
| 09:30 | `.github/workflows/scan.yml` | Sky intraday scan / Shadow snapshot | NONE |
| 09:50 | `.github/workflows/scan.yml` | Sky intraday scan / Shadow snapshot | NONE |
| 10:15 | `.github/workflows/scan.yml` | Sky intraday scan / Shadow snapshot | NONE |
| 14:30 | `.github/workflows/shadow-outcome-backfill.yml` | Same-day Shadow outcome completion | NONE |
| 14:50 | `.github/workflows/w6-forward-execution-evidence.yml` | Forward L1 / execution evidence | NONE |
| 16:30 | `.github/workflows/shadow-promotion-dashboard.yml` | W4 sample sufficiency / promotion dashboard | NONE |
| 16:50 | `.github/workflows/p0r-forward-risk-evidence.yml` | P0-R fail-closed risk evidence review | NONE |
| 17:10 | `.github/workflows/w3b-production-hardening.yml` | Runtime/E2E/container/Terraform hardening | NONE |

## Governance

1. GitHub Actions is the operational scheduler; ChatGPT Automations is not required for the core Sky pipeline.
2. All scheduled work remains Shadow/Paper/research/governance only.
3. No workflow may place live orders.
4. No position size may be inferred when user-specific capital / 1R inputs are not configured.
5. P0-R remains fail-closed. If W4 sample sufficiency or user risk inputs are unavailable, status must remain `NOT_EVALUABLE`.
6. W4 minimum gates remain:
   - >=200 evaluable samples
   - >=20 trading days
   - >=2 regimes
   - >=95% outcome completeness
   - <=20% single-symbol share
7. Counterfactual outcomes must never be represented as actual fills or realized P&L.
8. W6 evidence is execution evidence only and must not become a directional Alpha signal.
9. W3B hardening validates runtime reproducibility and does not authorize Production strategy changes.
10. Any paid data, new external credentials, irreversible deployment, or real-capital action still requires explicit user approval.

## Critical path

`Intraday Scan → W4 Outcome → W6 Execution → W4 Dashboard → P0-R → W3B → W0/P0-G`

## Notes

- TWSE trading-calendar gate in `scan.yml` prevents ordinary non-trading-day scans.
- GitHub artifact retention remains the evidence handoff mechanism.
- Production baseline remains unchanged.


## Notification Architecture

Canonical notification flow:

`GitHub Actions → GitHub Artifacts / Evidence → Telegram milestone alerts → ChatGPT on-demand analysis`

Telegram is intentionally event-driven, not chatty.

Notify only when:
- W4 transitions to `SAMPLE_READY` or `GOVERNANCE_REVIEW_READY`;
- P0-R transitions to `READY_FOR_P0R_REVIEW`;
- W6 transitions to `EXECUTION_CANDIDATE`;
- W4 / P0-R / W6 / W3B workflow has a material execution failure.

Do not notify for:
- normal scheduled runs;
- ordinary WAITING / HOLD / INSUFFICIENT_DATA states;
- unchanged repeated states;
- research intermediate output with no governance consequence.

ChatGPT is not part of the execution chain. It reads GitHub evidence on demand for analysis, interpretation and governance support.
