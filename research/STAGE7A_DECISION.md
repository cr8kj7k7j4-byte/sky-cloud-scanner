# Sky Stage 7A Research Decision Record

## Status
- Decision: **REJECT FOR PRODUCTION / RESEARCH_ONLY**
- Date: 2026-10-25
- Effective run: 40142773943
- Data fix included: Fugle historical 5m volume is interpreted as board lots; turnover uses price * lots * 1000.
- Production impact: NONE

## Pre-registration integrity
Rules remained fixed in:
- research/STAGE7A_PREREGISTRATION.md

The only post-run change before the effective result was a data-unit correction:
- Fugle 5m volume: lot
- turnover conversion: TWD/share * lots * 1000 shares/lot

No A1-A5 threshold was changed.

## Effective diagnostic funnel
- symbol_days: 42,525
- feature_ready: 37,643
- breadth >= 55: 3,155
- RS > 0: 17,132
- peer percentile >= 80: 8,201
- abnormal volume >= 1.5: 13,538
- gap in [-1%, +3%]: 31,453
- liquidity >= NT$20m: 18,439
- A1 feature pass: 117
- platform exists: 7,021
- A1 with platform: 34

## Results

### A1 Leadership
- N=14
- Win rate=28.6%
- EV=-0.481R
- PF=0.324
- 2025: N=6, EV=+0.189R, PF=1.616
- 2026: N=8, EV=-0.983R, PF=0.032
- EV at 0.45% cost=-0.542R
- Stable positive: NO

### A2 Momentum continuation
- N=9
- Win rate=11.1%
- EV=-0.631R
- PF=0.241
- 2025: N=4, EV=-0.010R, PF=0.979
- 2026: N=5, EV=-1.128R, PF=0.000
- EV at 0.45% cost=-0.689R
- Stable positive: NO

### A3 Volatility contraction
- N=0
- Stable positive: NO

### A4 Momentum + contraction
- N=0
- Stable positive: NO

### A5 Anti-chase leadership
- N=8
- Win rate=25.0%
- EV=-0.674R
- PF=0.178
- 2025: N=3, EV=+0.127R, PF=1.480
- 2026: N=5, EV=-1.155R, PF=0.000
- EV at 0.45% cost=-0.745R
- Stable positive: NO

## Governance conclusion
1. No Stage 7A hypothesis passes the pre-registered stable-positive gate.
2. Do not promote A1-A5 into P0-C, P0-O, P0-R, or production ranking.
3. Do not tune these exact thresholds further from this sample.
4. The corrected turnover conversion is retained as a P0-DATA contract requirement.
5. Current-listed 100-name universe remains survivorship-biased, so even a future positive result in this sample would not be enough for production promotion.

## Next allowed research direction
Priority is not local threshold mining.

Proceed in this order:
1. P0-DATA production contract and CI validation.
2. End-to-end Production Acceptance Test across Data -> Market -> Feature -> Decision -> Ranking -> Risk -> Execution -> Position -> Ledger.
3. Build a historical point-in-time universe to reduce survivorship bias.
4. Only then resume broader Alpha research with untouched OOS / walk-forward validation.

Stage 7A remains archived as tested-and-rejected.
