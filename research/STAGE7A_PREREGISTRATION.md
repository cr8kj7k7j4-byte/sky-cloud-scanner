# Stage 7A Broader Market Alpha Pre-Registration

Status: RESEARCH_ONLY
Date: 2026-10-25
Production impact: NONE

## Fixed data and execution
- No event/MOPS features.
- Universe: deterministic 50 TWSE + 50 TPEx current-listed sample.
- Known limitation: survivorship bias.
- Data: Fugle 5-minute bars, 2025-01-01 to 2026-10-22.
- Entry price < 100.
- First qualifying breakout 09:30-11:00.
- Entry next bar open + 1 legal tick.
- Structural stop, risk 1.0%-2.5%, target 2R, max 24 bars.
- Same-bar ambiguity: stop first.
- Cost tests: 0.25%, 0.35%, 0.45%.

## Fixed observable features
1. 09:30 market breadth.
2. 09:30 cross-sectional relative strength.
3. 09:30 cross-sectional percentile proxy.
4. First-30-minute abnormal volume versus prior 10 days.
5. Prior 5-day momentum.
6. Prior 3-day range / prior 10-day median range.
7. Overnight gap.
8. Prior 10-day median turnover proxy.

## Hypotheses
A1 Leadership:
- breadth >= 55
- relative strength > 0
- percentile >= 80
- first-30m abnormal volume >= 1.5
- gap -1% to +3%
- prior 10-day median turnover >= NT$20m

A2 Momentum continuation:
- A1
- prior 5-day momentum > 0

A3 Volatility contraction:
- A1
- prior 3d/10d range ratio <= 0.80

A4 Momentum + contraction:
- A1
- prior 5-day momentum > 0
- contraction ratio <= 0.80

A5 Anti-chase leadership:
- A1
- first-30m stock return <= 4%
- breakout-bar volume ratio <= 4
- gap <= 2%

## Stable-positive research gate
All must pass:
- total N >= 100
- 2025 N >= 30
- 2026 N >= 30
- total EV > 0 and PF > 1
- 2025 EV > 0 and PF > 1
- 2026 EV > 0 and PF > 1
- EV > 0 at 0.45% cost

Even if passed, status remains RESEARCH_ONLY until broader-universe OOS, walk-forward, leakage, and cost review are completed.
