# W3A Source / Acquisition Plan — Top100 Velocity Full-Market Intraday Data

Date: 2026-10-26
Status: SOURCE_RESEARCH_COMPLETE / PURCHASE_NOT_AUTHORIZED

## Objective
Find a data path capable of reconstructing causal full-market Top100 gainers membership at intraday timestamps for TWSE + TPEx.

## Verified source findings

### 1. TWSE official historical trading data
Official TWSE information service explicitly lists historical trading data including:
- order files;
- trade files;
- disclosure files.

TWSE Data E-Shop also states that users may request customized historical files for specific periods / data types.

Assessment:
- Highest provenance quality for listed-market historical microstructure.
- Must confirm exact file schema, timestamps, historical coverage, licensing, and price for the 2023+ research window.
- Likely the preferred source for TWSE if quotation is commercially reasonable.

### 2. TPEx official data
Required for promotion-grade full Taiwan-market coverage.
Exact historical intraday/order/disclosure product and acquisition terms still require source-level confirmation.
No promotion-grade Top100 reconstruction may proceed with TWSE-only data if the eligible universe includes TPEx.

### 3. Fugle
Verified current plan capabilities include:
- intraday market snapshots / movers;
- intraday quote, candles, trades;
- historical candles;
- WebSocket subscriptions;
- listed / OTC coverage.

Current published individual plans:
- Developer: NT$1,499/month, 300 WebSocket subscriptions.
- Advanced: NT$2,999/month, 2,000 WebSocket subscriptions.

Historical stock price coverage is stated to extend back to 2010 for listed/OTC stocks, but the documented historical endpoint is candles. Current docs do not establish that it supplies historical full-market point-in-time Top100 snapshots or historical order-book states sufficient for promotion-grade reconstruction.

Assessment:
- Strong candidate for prospective live Top100 construction and Shadow/Paper collection.
- Not yet proven sufficient as the sole historical source for causal full-market reconstruction.

## Acquisition hierarchy

Priority A:
1. TWSE official customized historical files for 2023+ order/trade/disclosure data.
2. TPEx equivalent official historical intraday / order / trade / disclosure data.

Priority B:
3. Commercial Taiwan vendor only if it materially lowers acquisition / engineering cost while preserving PIT reproducibility and licensing rights.

Priority C:
4. Fugle for prospective live scanner / Shadow evidence, not assumed to solve historical PIT until verified.

## Required vendor questions
Before any purchase:
- Does the dataset cover every listed/OTC common stock point-in-time?
- Can we reconstruct prior close and intraday price at synchronized timestamps?
- Are trades timestamped at sufficient granularity?
- Are bid/ask or disclosure snapshots included historically?
- Are order additions/cancels available?
- Are symbol listing/delisting/suspension states included?
- What is the start date?
- What is the file format and approximate data volume?
- Is research/backtest storage and derived-feature use permitted?
- Are there redistribution restrictions?
- What is the total cost for 2023-01-01 through present?
- Are updates available prospectively?

## Decision rule
Do not purchase based on brand or generic market-data claims.

Preferred source = lowest total cost that passes:
1. PIT causality;
2. >=95% governed-universe coverage;
3. timestamp synchronization;
4. legal reproducibility for Sky research;
5. sufficient depth for Top100_t reconstruction.

Any paid purchase requires explicit user approval because it creates an external financial commitment.
