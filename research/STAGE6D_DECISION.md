# Sky Stage 6D Research Decision Record

## Status
- Decision: **REJECT FOR PRODUCTION / RESEARCH_ONLY**
- Date: 2026-10-25
- Run: 40139795575
- Scope: pre-registered reaction-first event-day research
- Production impact: NONE

## Pre-registration integrity
Rules were frozen before observing the result in:
- research/STAGE6D_PREREGISTRATION.md

No threshold was changed after the first result.

## Results

### H1 — Delayed confirmation
- N=41
- Win rate=19.5%
- EV=-0.538R
- PF=0.138
- 2025 EV/PF=-0.645R / 0.102
- 2026 EV/PF=-0.400R / 0.203
- Stable positive: NO

### H2 — Relative-strength persistence
- N=23
- Win rate=21.7%
- EV=-0.585R
- PF=0.147
- 2025 EV/PF=-0.674R / 0.066
- 2026 EV/PF=-0.417R / 0.325
- Stable positive: NO

### H3 — Pullback / reclaim
- N=97
- Win rate=22.7%
- EV=-0.658R
- PF=0.191
- 2025 EV/PF=-0.504R / 0.245
- 2026 EV/PF=-0.761R / 0.164
- Stable positive: NO

### H1 + Anti-Chase
- N=18
- Win rate=16.7%
- EV=-0.598R
- PF=0.118
- 2025 EV/PF=-0.579R / 0.190
- 2026 EV/PF=-0.617R / 0.039
- Stable positive: NO

### H3 + Anti-Chase
- N=62
- Win rate=27.4%
- EV=-0.548R
- PF=0.233
- 2025 EV/PF=-0.513R / 0.240
- 2026 EV/PF=-0.588R / 0.225
- Stable positive: NO

## Cost sensitivity
All five hypotheses remain negative at:
- 0.25% cost
- 0.35% cost
- 0.45% cost

Therefore the rejection is not caused only by the base 0.35% cost assumption.

## Interpretation
1. Delaying the first breakout to 09:30 did not rescue expectancy.
2. Relative-strength persistence from 09:20 to 09:30 did not produce a stable edge.
3. Pullback/reclaim execution did not produce a stable edge.
4. The tested Anti-Chase overlay reduced sample count but did not turn the strategy positive.
5. Event-day price-reaction logic, under this fixed 100-name current-listing sample and execution model, is not sufficient as a production Alpha source.

## Governance conclusion
- Do not promote H1, H2, H3, H1+Anti, or H3+Anti into P0-C or P0-R.
- Do not tune these exact thresholds further in production.
- Keep P0-EVT as evidence/context.
- Record these hypotheses as tested-and-rejected to avoid repeated research cycling.

## Recommended next research direction
Stop local threshold optimization on event-day 5-minute setups.

The next research program should shift to one of two higher-value directions:

### A. Broader market Alpha research
Use a broader, less survivorship-biased historical universe and test non-event predictors:
- market regime
- cross-sectional relative strength
- liquidity
- abnormal volume
- volatility contraction/expansion
- multi-day momentum
- overnight gap behavior
- sector/industry strength once official historical mapping is available

### B. Event research at a slower horizon
Treat MOPS events as medium-horizon context rather than intraday triggers:
- T+1 to T+5 abnormal return
- post-event drift
- earnings/revenue/guidance category separation
- event surprise magnitude where objectively measurable
- sector-adjusted abnormal return

Both paths remain RESEARCH_ONLY until independent OOS / walk-forward / leakage / cost review passes.
