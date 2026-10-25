# W3A｜Intraday PIT Historical Replay Dataset — Build & Audit Status 2026-10-25

## Current status

**DATA ENGINEERING ACTIVE / W2 DATA_BLOCKED**

Production impact: **NONE**

Production baseline remains: Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP.

## DATA STATUS

### PIT Universe
- 2023+ Historical Universe gate: **PASS**
- Current-universe backward sampling remains prohibited.
- Canonical whole-universe downloads use PIT membership intervals.

### Whole-Universe Intraday History
Two real GitHub Actions paths are executing:
- monolithic controlled-pacing export: run `40197918327`
- canonical 20-shard export: run `40198835143`

The sharded pipeline:
- max-parallel = 1
- clamps each symbol to actual PIT membership window
- aggregates exactly 20 shard artifacts
- runs symbol-day coverage audit
- requires >=95% symbol and symbol-day coverage
- rejects duplicates and out-of-membership bars

Final source coverage is not declared PASS until the aggregate audit finishes.

### TAIEX Benchmark
**PASS**

Verified Fugle IX0001 5-minute history:
- start: 2023-05-23 09:00 +08:00
- end: 2026-10-22 13:30 +08:00
- bars: 45,760
- Actions run: `40199386467`
- artifact: `12601415748`
- digest: `sha256:9ff95cc99580716c0200dc1838b530459ebe0cab105ec555bdfbd0abe78dfde3`

This resolves the explicit intraday market benchmark source.
Equal-weight cross-sectional return remains diagnostic and is not substituted for TAIEX.

## SECTOR STATUS

### Current Official Anchor
Latest normalized official anchor:
- TWSE mapped: 1,087
- TPEx mapped: 894
- total mapped: 1,981
- unresolved TWSE TDR symbols: 9103, 9105, 9110, 9136

Canonical namespace:
- sector_code
- Chinese sector display name
- raw source value
- source URL / source_as_of

Current anchor is **not historical PIT by itself**.

### Effective-Dated History
Event-sourced reconstruction is implemented.

Important parser correction:
- ROC date regex fixed
- symbol regex fixed
- source provenance retained
- old_sector unknown is allowed only as a fail-closed boundary:
  verified post-change interval is preserved; pre-change history remains `PRE_CHANGE_SECTOR_UNKNOWN`.

Sector history still requires complete official event-source coverage for the governed research window.

## FEATURE STATUS

Decision-time objective primitives can now be reconstructed causally from 5-minute bars using only bars at or before decision time:
- feature_cutoff_timestamp
- entry_reference_price / price
- volume
- cumulative VWAP
- price_vs_vwap_pct
- VWAP slope
- day return
- gap
- session low/high at decision
- session position

The following are intentionally **not invented**:
- MTF short/mid/long state
- Phase
- ATR14
- extension ATR
- breakout-bar ATR
- RVOL / volume z-score
- resistance distance
- stop-distance logic

Their status remains: `FROZEN_ALPHA_INPUT_REQUIRED`.

## FROZEN v1.4 REPLAY STATUS

Machine audit scans Production `src/*.py`.

Current result: `FROZEN_ALPHA_INPUT_REQUIRED`.

Observed facts:
- registry metadata is not executable rule logic
- no complete executable frozen v1.4 historical replay adapter exists
- current CORE_RULE_IDS does not cover all W2 10-rule columns
- historical canonical decision stream is absent
- current scanner stores Top-N truncated candidate snapshots
- research-only strategy builder is not an acceptable v1.4 substitute

Therefore W3A will not reconstruct missing Alpha thresholds or rules.

## COST STATUS

Fixed research stress scenarios are implemented:
- primary: 0.45% round-trip
- stress: 0.65% round-trip

Cost drag is converted to R using planned risk.

Existing supplied `net_r_045` / `net_r_065` values are consistency-checked.
Mismatch => `CONFLICT` => fail closed.

These cost scenarios are not empirical spread/slippage evidence.

## AUDIT STATUS

Implemented:
- coverage audit
- leakage audit
- timestamp causality audit
- sector interval validity
- candidate pool completeness
- cost conflict detection
- survivorship control
- full source SHA256 lineage
- versioned manifest
- W2 runner handoff

W2 efficacy executes only when all fail-closed gates PASS.

## CURRENT W2 READINESS

**DATA_BLOCKED / HOLD**

The remaining hard dependency is not a missing research formula. It is the absence of a canonical frozen Production-v1.4 historical decision source / executable replay adapter capable of producing:
- full 10-rule gate outputs
- full untruncated contemporaneous candidate pool
- MTF / Phase / Setup / Trigger / Anti-Chase states
- planned entry / stop / targets
- gross RR / execution-adjusted RR

Without that evidence, Candidate Pool / Ranking, Execution Context and Outcome Join cannot be represented as canonical Production-v1.4 replay evidence.

## Governance

- No Alpha logic changed.
- No Production Rule changed.
- No rejected research strategy substituted.
- No current universe used for historical backfill.
- No current sector snapshot treated as historical PIT without event evidence.
- No future bars used in features.
- No missing spread/slippage imputed to zero.
- No W2 Rule Contribution may run while readiness is DATA_BLOCKED.