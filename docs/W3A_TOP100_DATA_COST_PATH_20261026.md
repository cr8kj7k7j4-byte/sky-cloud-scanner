# W3A Top100 Data Path — Cost / Coverage Decision 2026-10-26

Status: EVIDENCE_UPDATE / PURCHASE_NOT_AUTHORIZED

## Key finding

TWSE Data E-Shop publishes historical transaction-file pricing:
- Historical order file: NT$10,000 per month (all)
- Historical trade file: NT$10,000 per month (all)
- Historical disclosure file: NT$5,000 per month (all)

For 2023-01 through 2026-10 inclusive = 46 months:
- all three TWSE files would be approximately NT$1,150,000 before any TPEx equivalent cost.

Therefore full official microstructure purchase is NOT the first acquisition path for the Top100 Velocity research question.

## Cheapest-first research path

### Path A — Fugle historical 1-minute reconstruction
Fugle documented historical candles:
- listed / OTC stocks;
- 1m / 3m / 5m / 10m / 15m / 30m / 60m intervals;
- intraday minute history from 2023-05-23;
- historical endpoint rate limit currently 60 requests/minute across individual plans.

Research question:
Can we causally reconstruct full-market Top100_t from:
- prior close;
- synchronized 1-minute close;
- interval / cumulative volume;
- point-in-time symbol membership?

This would be sufficient to test the core Top100 + Velocity hypothesis even without order-book microstructure.

Hard unresolved checks:
1. historical delisted-symbol accessibility;
2. complete historical symbol universe / listing lifecycle;
3. corporate action / prior-close causality;
4. full TWSE + TPEx coverage across the governed period;
5. timestamps and missing-bar policy;
6. reproducibility under API license.

If all pass, this is the preferred low-cost route for W2 alpha comparison.

### Path B — Official trade + disclosure only
If Path A cannot meet PIT / coverage requirements, next test whether order files are unnecessary for the initial Top100 alpha comparison.

Top100 + Velocity requires price / volume / prior-close / universe history, not historical order messages.

Do not buy historical order files unless W6 microstructure research specifically requires them.

### Path C — Full official microstructure
Only for later W6 execution / order-flow research if independent evidence justifies the cost.

## Decision
1. Do not purchase TWSE full microstructure now.
2. First prove or reject Fugle full-market 1-minute PIT reconstruction.
3. If Fugle fails, price the minimum official file set needed for Top100.
4. Any paid acquisition remains a user-approval gate.
