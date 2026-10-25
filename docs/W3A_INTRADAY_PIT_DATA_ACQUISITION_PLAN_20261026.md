# W3A｜Intraday PIT Data Acquisition Plan — 2026-10-26

> Owner: W3A｜Sky Data & Feature Engineering
> Requested by: W0｜Sky Master Control
> Status: DATA ACQUISITION PLAN / NO PURCHASE AUTHORIZED
> Production impact: NONE

## 1. Current blocker

W3A replay framework is ENGINEERING COMPLETE, but promotion-grade historical intraday replay remains DATA_BLOCKED.

Existing 100-symbol 5m artifact:
- 2,704,785 bars
- period approx. 2023-05-23 through 2026-10-22
- max possible governed PIT-universe symbol coverage only ~4.8%–5.3%
- required gate >=95%

Therefore framework completeness must not be confused with research-data sufficiency.

## 2. Source options verified

### A. Fugle historical minute candles
Verified public documentation:
- supports listed / OTC / emerging stocks by symbol
- supports 1/3/5/10/15/30/60-minute bars
- minute history begins 2023-05-23
- single request date span must be <1 year
- daily update after market close
- requests are authenticated and rate-limited by plan

Strengths:
- direct fit for 5m replay
- same start date as current artifact
- likely simplest path to extend symbol breadth toward the governed PIT universe
- timestamped ISO-8601 bars

Limitations / open checks:
- actual account plan / request-rate capacity for ~2,000 symbols
- delisted/inactive symbol retrievability must be empirically verified
- API access through the currently connected Fugle content connector did not successfully return historical minute data in this control session; direct MarketData API credentials may still be required
- minute adjusted prices are not provided, so corporate-action handling must be explicit

Governance:
- use first as a feasibility/acquisition path only if credentials and rate limits allow
- do not claim >=95% until coverage audit actually passes

### B. TWSE Data E-Shop — Securities intra-day data with 5-level order book
Verified official product:
- start date: 1992-01-01
- available until about two months before order date
- all-market historical intraday data
- price: NT$5,000 per month
- internal-use-only restrictions
- customized files may require >=7 working days

Strengths:
- official source
- broad historical coverage
- strong PIT provenance
- suitable to reconstruct price / quote / spread context for listed securities

Limitations:
- paid
- TWSE listed market only; TPEx must be sourced separately
- data size / parsing / schema-version changes
- licensing is internal-use restricted

### C. TWSE Data E-Shop — Securities intra-day data with order type
Verified official product:
- start date: 2006-01-01
- available until one year before
- price: NT$10,000 per month
- internal-use-only

Use only if order-type information is required for a later W6 microstructure experiment.
Not required as first choice for current 5m W2 replay.

### D. TPEx Data E-Shop — historical trade file
Verified official product:
- historical trade file (MTH.zip)
- start date: 2022-11-01
- historical availability restrictions apply
- listed price shown: NT$10,000/month for external use

Strengths:
- official OTC source
- can cover TPEx side missing from a TWSE-only official route

Open checks:
- exact internal-use price / rights
- exact field granularity sufficient for 5m reconstruction
- historical quote/order-book companion products, if needed
- schema and timestamp semantics

### E. TWSE / TPEx public daily/open APIs
Useful for:
- PIT universe
- suspension / trading-status
- daily market state / after-market controls
Not sufficient by themselves for full intraday 5m whole-universe replay.

## 3. Recommended acquisition strategy

### Phase 1 — Zero-new-spend feasibility
1. Use current canonical PIT universe ledger to produce the complete symbol-period acquisition matrix.
2. Probe Fugle MarketData historical minute coverage across:
   - active TWSE symbols
   - active TPEx symbols
   - delisted/inactive historical members
   - corporate-action cases
3. Measure:
   - symbol coverage
   - date coverage
   - bar completeness
   - request throughput
   - retry/error rate
4. If >=95% PIT membership coverage can be reproduced with available access, proceed with Fugle-based backfill.

### Phase 2 — Official-source fallback
If Phase 1 cannot reach >=95%:
1. Use TWSE official 5-level historical product for listed-market history.
2. Use TPEx official historical products for OTC history.
3. Build exchange-specific parsers into the existing W3A replay builder.
4. Preserve raw files and source manifests.
5. Run coverage/leakage audits again.

This phase requires a user-approved paid purchase before acquisition.

## 4. Cost-control decision

Current recommendation:
- DO NOT purchase broker-flow data.
- DO NOT purchase TWSE order-type data yet.
- DO NOT purchase any historical dataset until Phase-1 Fugle feasibility is conclusively tested.
- If paid official data is required, prefer the minimum product that closes the PIT replay gap:
  - TWSE 5-level historical data before the more expensive order-type product.
  - TPEx minimum historical intraday product sufficient for 5m reconstruction.

## 5. Acceptance criteria

The acquisition path is accepted only if the reconstructed replay passes:
- PIT universe coverage >=95%
- market context coverage >=95%
- sector mapping coverage >=95% when claimed
- core Phase/Anti-Chase coverage >=95%
- OOS explicit
- outcome completeness >=95%
- cost-model completeness 100%
- leakage audit PASS
- survivorship audit PASS

## 6. Candidate consequences

Until the above passes:
- W2 remains HOLD / DATA_BLOCKED
- Overnight Reversal remains HOLD
- Dynamic Lead-Lag remains HOLD
- Broker Flow remains HOLD / DO_NOT_BUY NOW
- ACCEPT_FOR_PREREGISTRATION remains 0
- Production remains unchanged

## 7. Human intervention gate

No human action is required for architecture, governance, coding, or feasibility analysis.

User intervention is required only if:
- direct Fugle MarketData API credentials are needed and not already available to the runtime; or
- a paid TWSE / TPEx data purchase is required.

No paid purchase is authorized by this document.
