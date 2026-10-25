# W4 Forward Evidence Addendum — Top100 Gainers Context

Date: 2026-10-26
Status: EVIDENCE_COLLECTION_ONLY
Production impact: NONE

## Purpose

Test whether membership in the contemporaneous current-day Top100 gainers universe
adds forward incremental information to the current Sky Day Trading v1.4 evidence stream.

This is not a new trade rule and does not alter current candidate selection.

## Fields added to every available Paper / Shadow snapshot

- gainer_rank
- top100_gainer_member
- gainer_universe_size
- gainer_rank_source = current_snapshot_change_pct

The rank is computed from the same contemporaneous market snapshot available to the
scanner at observation time. It is not reconstructed from end-of-day data.

## Governance

- Current P0-O screening rank remains unchanged.
- P0-C decisions remain unchanged.
- P0-R decisions remain unchanged.
- No signal is promoted because it is in Top100.
- Top100 membership is FEATURE_ONLY / CANDIDATE_POOL context.
- Baseline A remains REJECTED_STANDALONE / ARCHIVED_NO_RETUNE.

## Future evaluation

When W4 sample sufficiency is reached, compare current v1.4 forward evidence by:
- Top100 member vs non-member;
- after-cost Expectancy;
- PF;
- win rate (secondary);
- Avg Win / Avg Loss;
- MAE / MFE;
- regime;
- time of day;
- data completeness.

This comparison may establish incremental candidate-pool value, but cannot by itself
promote a strategy or override P0-R / P0-G.
