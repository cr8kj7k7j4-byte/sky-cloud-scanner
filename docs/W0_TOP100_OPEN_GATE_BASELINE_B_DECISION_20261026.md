# W0 Decision — Top100 Velocity Baseline B / Open-Price Gate

Date: 2026-10-26

## User hypothesis tested
Monitor current-day Top100 gainers from the open and do not enter if the decision-time price is below the current trading day's opening price.

Only one rule changed versus Baseline A:
- entry_price > current-day 09:00 open.

Everything else remained frozen.

## Result

### 60-minute outcome
- n = 1,244
- Gross expectancy: -0.0690% / observation
- Gross PF: 0.875
- 0.45% cost expectancy: **-0.5190%**
- 0.45% PF: **0.393**
- 0.45% win rate: **26.13%**
- 0.65% stress expectancy: **-0.7190%**
- 0.65% PF: **0.287**

All 3 chronological folds are negative.
2023 / 2024 / 2025 / 2026 are all negative after 0.45% cost.

Compared with Baseline A:
- A: -0.4888%, PF 0.556
- B: -0.5190%, PF 0.393

Therefore the open-price gate did not improve the frozen Baseline A.

## Full-day diagnostic

To address the user's real trading intuition, the selected names were also followed from entry to market close rather than only for 60 minutes.

- Near-limit-up proxy (post-entry high >= +9.5% vs prior close): 48 / 1,244 = **3.86%**
- Mean MFE to close: **+1.54%**
- Median MFE: **+0.89%**
- 90th percentile MFE: **+3.81%**
- MFE >= +5%: **6.75%**
- Mean close return: **-0.13%**
- Mean close return after 0.45% round-trip cost: **-0.58%**

The +9.5% measure is a diagnostic proxy for approaching the Taiwan daily limit and is not an exact exchange limit-price reconstruction.

## Governance decision

**Baseline B: REJECTED_STANDALONE / ARCHIVED_NO_RETUNE**

This rejects the frozen mechanical implementation only.

It does NOT prove that the user's historical discretionary Top100 process had no edge. The discretionary process may have included information that was not yet encoded:
- very early opening acceleration;
- quality of the first impulse;
- tape / order-flow behavior;
- breakout location;
- sector synchrony;
- discretion around holding a runner rather than a fixed 60-minute exit.

Those must be formulated as new structural hypotheses before testing, not added retrospectively to rescue Baseline B.

Top100 gainers universe remains FEATURE_ONLY / CANDIDATE_POOL.
Production v1.4 remains unchanged.
