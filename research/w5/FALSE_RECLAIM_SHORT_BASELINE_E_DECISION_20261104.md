# W5｜False-Reclaim Short Baseline E — evidence-based closure proposal

Date: 2026-11-04
Research owner: W5 / W2
Decision recommendation: **REJECT_AFTER_COST_EXPECTANCY → ARCHIVED_NO_RETUNE**, pending W0 research-governance review.
Production impact: **NONE**; do not alter Sky Day Trading v1.4, automated trading, or risk settings.

## Frozen hypothesis and data
- Preregistration: `research/w5/FALSE_RECLAIM_SHORT_BASELINE_E_PREREGISTRATION_20261026.md`.
- Research window: 2026-01-01 to 2026-10-22; these historical observations are **not fresh OOS**.
- Intraday causal entry: prior strength → opening-price retest → reclaim → failed reclaim below open; enter next 1-minute open before 09:15 within four legal ticks below session open.
- Primary outcome: 60-minute stop-aware short return.
- Preregistered round-trip research cost: 0.45%; stress cost: 0.65%.
- Historical point-in-time short-sale eligibility and borrowability are not gated; the economic backtest does **not** establish live short availability.

## Engineering readback
- Initial full-data attempt Run [40329668748](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/40329668748): 20 download shards succeeded; backtest failed early due to `ModuleNotFoundError: No module named 'requests'`.
- Recovery Run [40418642301](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/40418642301): tests and backtest succeeded; artifact `baseline-e-recovery-result-40418642301` uploaded.
- Independent rerun Run [40418589493](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/40418589493): all download shards and backtest successful; result artifact `baseline-e-result-40418589493` uploaded.
- The two successful runs reported identical primary economic metrics; source lineage from GitHub job logs.

## Reported backtest outcomes
| Metric | Gross | 0.45% round-trip | 0.65% stress |
|---|---:|---:|---:|
| Evaluable 60-minute trades | 10,732 | 10,732 | 10,732 |
| Mean return per trade | +0.2241% | **-0.2259%** | **-0.4259%** |
| Profit factor | 1.792 | **0.640** | **0.458** |
| Win rate | 24.30% | 21.55% | 19.87% |

- Candidate signals selected: 13,399.
- 0.45% half-year mean return: 2026-H1 -0.2298% (n=6,656; PF 0.637); 2026-H2 -0.2195% (n=4,076; PF 0.646).
- The backtest's recorded decision: `REJECT_AFTER_COST_EXPECTANCY`.
- All figures are simulated, before live-availability constraints; not actual executions or predictive win probabilities.

## Gate disposition and governance
- **Gate 5 cost viability: FAIL**; mean return < 0 and PF < 1 for the preregistered primary cost. The stress case also fails.
- **Gate 2 fresh OOS**: not established; existing 2026 data is reused research evidence.
- **Execution viability**: historical short eligibility, borrow and real fills remain unverified, but additional data cannot turn this already-negative research result into an approved strategy without a separately preregistered structural hypothesis.
- Proposed status: `REJECT` for the tested version; `ARCHIVED_NO_RETUNE` to prevent threshold / Top-N / time / weights / stop-target changes to rescue this exact architecture.
- This does **not** reject all short-side strategies. A successor requires a materially independent, prospectively preregistered target/label/data or execution architecture with untouched evaluation period.
- No additional Baseline E tuning, Production deployment, trade signals, new short-side schedule, or automatic orders are authorized.
- W0 to review the archival decision and decide whether/how to modify canonical registries. This document is a proposed research closure, not a claim of W0 approval.

## Validation checklist
- [x] Preregistration located.
- [x] Recovery and independent workflow-run successes verified.
- [x] Produced result artifacts verified by GitHub Actions metadata.
- [x] Primary, stress, half-year and failure statistics read from real job logs.
- [x] Cost gate outcome matches the preregistration's explicit REJECT rule.
- [ ] W0 governance approval and canonical registry update.
- [ ] New structural short candidate — not implied or required by this rejected baseline.
