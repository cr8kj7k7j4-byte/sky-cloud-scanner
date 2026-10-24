# Sky Stage 6B / 6C Research Decision Record

## Status
- Decision: **REJECT FOR PRODUCTION / RESEARCH_ONLY**
- Date: 2026-10-25
- Scope: Stage 6B true MOPS catalyst research + Stage 6C event × market × reaction interaction research
- Production impact: **None. Do not promote any Stage 6B/6C score, bucket, or interaction signature into P0-C or P0-R.**

## Stage 6B
- Event source: MOPS historical material information
- Trade rows: 707 in the validated Stage 6B scoring run
- Overall expectancy: -0.436R
- Profit factor: 0.281
- 2025 expectancy/PF: -0.450R / 0.288
- 2026 expectancy/PF: -0.415R / 0.268
- Event Score, Catalyst Score, Source Confidence and Freshness did not produce a stable monotonic positive-expectancy selection rule.

## Stage 6C
- Trade rows enriched: 793
- Overall expectancy: -0.416R
- Profit factor: 0.317
- Stable positive candidates: **0**

### Best-looking but rejected interaction groups
1. `M+|RS+|P+|V+|G-`
   - N=18, EV=+0.175R, PF=1.490
   - 2025: N=13, EV=-0.064R, PF=0.844
   - 2026: N=5, EV=+0.797R, PF=4.465
   - Rejected: insufficient sample and unstable across years.

2. `M-|RS+|P+|V-|G-`
   - N=23, EV=+0.050R, PF=1.187
   - 2025: N=13, EV=+0.157R, PF=1.692
   - 2026: N=10, EV=-0.089R, PF=0.724
   - Rejected: unstable across years.

## Governance conclusion
1. P0-EVT remains an **evidence/catalyst layer**, not a directional or executable trade-signal engine.
2. High Event Score / Catalyst Score must not be interpreted as a higher true win probability.
3. No Stage 6B/6C rule may bypass P0-C Decision Engine, P0-R Risk Engine, or normal Anti-Chase / RR gates.
4. Do not tune production thresholds from these results.
5. Do not promote any positive subgroup unless it independently passes pre-registered OOS, walk-forward, cost/slippage sensitivity, leakage review, and minimum-sample gates.

## Next research direction
Do **not** continue arbitrary bucket mining.

The next allowed research path is a pre-registered **reaction-first hypothesis test**:
- Event remains context only.
- The predictive candidate must come from observable post-event market reaction, not event importance.
- Pre-register a small set of hypotheses before running them.
- Require directional stability across time splits.
- Prefer a broader / less survivorship-biased universe and official historical sector mapping before claiming sector effects.

Recommended hypothesis family:
1. Delayed confirmation after event-day open rather than first breakout.
2. Relative-strength persistence versus market breadth after the first 15–30 minutes.
3. Pullback/reclaim architecture instead of immediate breakout chasing.
4. Explicit no-trade filters for event-driven gap extension and excessive RVOL.

All future tests remain **RESEARCH_ONLY** until governance promotion criteria are met.
