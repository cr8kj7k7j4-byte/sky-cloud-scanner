# Sky Stage 6D Reaction-First Pre-Registration

## Governance
- Status: PRE-REGISTERED / RESEARCH_ONLY
- Date: 2026-10-25
- Production impact: NONE
- Event information is context only. No event score may directly trigger a trade.
- No threshold in this document may be changed after the first Stage 6D result is observed without creating a new versioned candidate.

## Data
- Event source: historical MOPS material information.
- Same-day eligibility only when announcement time <= 08:30; otherwise use next trading day.
- Price data: Fugle historical 5-minute bars.
- Universe: deterministic 50 TWSE + 50 TPEx current-listed sample.
- Known limitation: survivorship bias remains.
- Price cap: entry < NT$100.
- Trading costs: 0.35% round-trip sensitivity plus one legal tick entry slippage.
- Same-bar stop/target ambiguity: stop first.

## Fixed evaluation splits
- 2025: development-era historical split.
- 2026: temporal validation split.
- A candidate may only be labelled stable-positive when:
  - total N >= 30
  - 2025 N >= 10
  - 2026 N >= 10
  - total EV > 0 and PF > 1
  - 2025 EV > 0 and PF > 1
  - 2026 EV > 0 and PF > 1
- Stable-positive still does NOT qualify for production. Separate OOS / walk-forward is mandatory.

## Fixed market-reaction measurements
At 09:20 and 09:30:
- stock return from open
- median cross-sectional return of available sample
- market breadth = percent of sample above its open
- stock relative strength = stock return - cross-sectional median
- peer percentile proxy = stock return percentile in the sample

The peer percentile is NOT an official sector score.

## Hypothesis H1 — Delayed confirmation
Entry architecture:
- Do not trade before 09:30.
- At/after 09:30 and before 11:00, first qualifying platform breakout.
Filters fixed before run:
- 09:30 relative strength > 0
- 09:30 peer percentile >= 70
- 09:30 market breadth >= 50
- opening gap between -1% and +3%
- breakout bar volume ratio >= 1.5
- structural risk 1.0% to 2.5%
Exit:
- 2R target
- structural stop
- max 24 five-minute bars.

## Hypothesis H2 — Relative-strength persistence
Same execution as H1, plus persistence:
- 09:20 relative strength > 0
- 09:30 relative strength > 0
- 09:30 relative strength >= 09:20 relative strength
- 09:30 peer percentile >= 70
- 09:30 market breadth >= 50
- opening gap between -1% and +3%.

## Hypothesis H3 — Pullback / reclaim
Do not buy the first breakout.
Between 09:30 and 11:00 require:
1. price has first traded above the first-30-minute high;
2. later closes back at or below that first-30-minute high;
3. then closes back above the first-30-minute high;
4. reclaim bar volume ratio >= 1.5;
5. stop = lowest low from pullback start through reclaim;
6. structural risk 1.0% to 2.5%;
7. 09:30 relative strength > 0 and peer percentile >= 70;
8. gap between -1% and +3%.
Entry next bar open + one legal tick.
Exit 2R / stop / max 24 bars.

## Hypothesis H4 — Anti-extension overlay
Apply to H1 and H3:
- reject gap > +3%
- reject gap < -1%
- reject entry-bar volume ratio > 4.0
- reject stock return from open at trigger > +5%
- reject risk > 2.5%
This hypothesis tests whether explicit anti-chase veto improves EV/PF; it is not a separate signal.

## Required output
For H1, H2, H3, H1+H4 and H3+H4:
- N
- win rate
- expectancy in R
- profit factor
- 2025 metrics
- 2026 metrics
- cost sensitivity at 0.25%, 0.35%, 0.45%
- stable-positive flag.

## Promotion rule
No Stage 6D hypothesis may enter P0-C, P0-R, or production scanning automatically.
Any positive result remains RESEARCH_ONLY pending:
- wider less-survivorship-biased universe
- separate OOS
- walk-forward
- leakage audit
- cost/slippage sensitivity
- explicit user approval.
