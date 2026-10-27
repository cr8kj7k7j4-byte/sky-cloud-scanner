# W0 / W1 Swing Challenger V1.1 Replay Review — 2026-10-28

Evidence: GitHub Actions run #40418729232, SUCCESS. 2,009 source symbols; 3,319 signal-level trades per exit variant. Frozen rule source: research/SKY_SWING_CHALLENGER_V1_1_PREREGISTRATION.md.

| Exit | Roundtrip cost | Win rate | Mean net trade return | PF | Mean net R |
|---|---|---|---|---|---|
| FIXED_3R | 0.45% | 29.98% | -0.3859% | 0.8224 | -0.2752 |
| FIXED_3R | 0.65% | 29.50% | -0.5859% | 0.7468 | -0.4047 |
| MA20_TRAIL | 0.45% | 23.62% | +0.3153% | 1.1501 | +0.1008 |
| MA20_TRAIL | 0.65% | 22.99% | +0.1153% | 1.0512 | -0.0287 |
| SWING10_TRAIL | 0.45% | 23.32% | +0.2546% | 1.1165 | +0.0903 |
| SWING10_TRAIL | 0.65% | 22.57% | +0.0546% | 1.0233 | -0.0392 |

## Research adjudication

- FIXED_3R variant: REJECT on negative mean net returns and PF < 1 for both costs.
- MA20_TRAIL: HOLD, prioritized for further verification; positive net percent return at both costs, but negative net R at 0.65% cost.
- SWING10_TRAIL: HOLD, thin 0.65% edge, negative net R.
- Formal V1.1 conclusion: HOLD, not Production eligible. No automatic or small-live execution authorization.

## Missing verification gates

1. Time-ordered out-of-sample and >=3 walk-forward folds.
2. Bull/Neutral/Bear split and per-year stability.
3. Position overlap, max concurrent positions, portfolio drawdown, capacity and concentration.
4. PIT causality, corporate action adjustment and exact-rule code audit.
5. Genuine prospective Shadow/Paper observations and execution-adjusted cost evidence.
6. Review discrepant net-% versus net-R expectancy; do not cherry-pick favorable units.

Recorded cumulative signal-sequence drawdown is not a portfolio drawdown. The backtest workflow succeeding is not equivalent to Promotion. Preserve frozen preregistration and Production baseline unchanged.

Current W4 (2026-10-28 morning): source paper files 0, eligible runs 0, samples 0. Scanner upstream output recovery remains critical.
