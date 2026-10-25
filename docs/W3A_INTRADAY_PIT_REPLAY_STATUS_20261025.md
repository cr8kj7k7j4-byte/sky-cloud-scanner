# W3A｜Intraday PIT Historical Replay Dataset — Build & Audit Status 2026-10-25

## Current status

**W3A DATA MAINTENANCE / HISTORICAL v1.4 FULL-RULE REPLAY CLOSED BY W0**

Superseding governance:
- `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`
- Historical v1.4 full-rule replay is **NOT FULLY RECONSTRUCTABLE from the current GitHub SSOT**.
- W2 formal status: **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**.
- W3A must maintain PIT/data/lineage and must not synthesize missing v1.4 Alpha rules.
- Current P0 critical path is **W4 → P0-R / W6 → W3B → W0/P0-G**.

Production impact: **NONE**

Production baseline remains: Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP.

## DATA STATUS

### PIT Universe
- 2023+ Historical Universe gate: **PASS**
- Current-universe backward sampling remains prohibited.
- Canonical whole-universe downloads use PIT membership intervals.

### Whole-Universe Intraday History
**PASS**

Canonical corrected PIT cache reconciliation:
- source raw cache: legacy run `40198835143`
- corrected workflow: `40221377923`
- persisted/audited PIT intervals: 2,029
- symbols with bars: 2,022
- symbol coverage: 99.8519%
- symbol-day coverage: 98.9071%
- minimum daily coverage: 97.3726%
- retained 5m bars: 54,187,242
- removed out-of-membership bars: 4,819,372
- duplicate bars: 0
- conflicting duplicates: 0
- out-of-membership bars after reconciliation: 0
- parse errors: 0

This clears the >=95% whole-universe market-raw-data source gate.

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
- Git-history provenance confirms the historical scanner documented the conceptual A+ gate chain but did not preserve executable canonical W2 10-rule outputs
- `first_gate` is an executable eligibility/liquidity primitive, not the W2 `market_gate`
- the deterministic P0-S 5m breakout family is formally archived/rejected and cannot substitute for v1.4 Setup/Trigger
- the trigger-slip Anti-Chase proxy is explicitly rejected as a standalone hard gate
- current CORE_RULE_IDS does not cover all W2 10-rule columns
- historical canonical decision stream is absent
- current scanner stores Top-N truncated candidate snapshots
- research-only strategy builder is not an acceptable v1.4 substitute

A fail-closed evidence-preserving adapter now exists:
- `research/frozen_v14_evidence_replay_adapter.py`
- preserves PIT-safe observed fields
- only preserves a canonical rule boolean when the formal provider registry allows it and the historical row already contains it
- otherwise forces the rule to `None` and blocks W2 efficacy

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

**HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**

The data-engineering source layer is no longer the primary blocker:
- corrected whole-universe 5m raw source: PASS
- PIT Universe: PASS
- TAIEX benchmark: PASS

The remaining limitation is authoritative historical Production-v1.4 rule provenance, which W0 has formally classified as not fully reconstructable from the current SSOT.

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

## 2026-10-26 Governance Closure

GitHub Issue #81 is closed as `not_planned` under the W0 governance decision.

Reason:
- W3A data engineering and source lineage are complete enough for canonical PIT/raw-market maintenance.
- The original issue's final objective—historical Production-v1.4 full-rule efficacy replay—cannot be completed without an authoritative frozen implementation or complete historical decision snapshot.
- W3A is prohibited from inventing or retrospectively reconstructing those missing Alpha rules.

Re-open condition:
- W0/P0-G accepts an authoritative `FROZEN_CANONICAL_IMPLEMENTATION` or `HISTORICAL_SNAPSHOT`.
