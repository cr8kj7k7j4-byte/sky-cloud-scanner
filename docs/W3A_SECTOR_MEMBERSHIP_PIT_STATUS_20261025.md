# W3A｜Effective-Dated Sector Membership Reconstruction — 2026-10-25

## Current conclusion
**ENGINEERING READY / SOURCE COVERAGE DATA_BLOCKED**

The previous highest-priority blocker:
`EXTERNAL_DATA_REQUIRED:EFFECTIVE_DATED_HISTORICAL_SECTOR_MEMBERSHIP`
is no longer an undefined problem. The reconstruction method is now formalized.

## Method
Use an event-sourced model:

`current official sector snapshot + official historical sector-change events → effective-dated sector intervals`

Do **not** backfill today's sector classification into prior dates.

## New implementation
- `src/sector_membership_events.py`
  - parses official announcement text with:
    - symbol
    - old sector
    - new sector
    - effective date
  - reconstructs intervals backward from current official sector state
  - fails closed if the event chain does not reconcile with current state
- `tests/test_sector_membership_events.py`
  - announcement parser test
  - interval reconstruction test
  - chain-mismatch fail-closed test
- `research/SECTOR_MEMBERSHIP_PIT_SOURCE_REGISTRY_20261025.json`
  - formal official-source registry

## Verified official-source pattern

### Current sector snapshots
- TWSE OpenAPI company basic data
- TPEx OpenAPI company basic data

### Historical sector-change announcements
Verified official announcement evidence currently includes:
- TWSE 2023 classification adjustment, effective 2023-07-03
- TPEx 2023 classification adjustment, effective 2023-07-03
- TPEx 2024 classification adjustment, effective 2024-06-03
- TPEx 2025 classification adjustment, effective 2025-06-02
- TPEx 2026 classification adjustment, effective 2026-06-01

The official rules also establish that listed-company industry categories are periodically reviewed and re-announced when changed.

## Remaining hard source gap
Annual TWSE adjustment/no-change evidence for:
- 2024
- 2025
- 2026

has not yet been verified in the canonical source registry.

This is a **source coverage** blocker, not an engineering blocker.

## Gate
Until all governed years/exchanges have either:
1. official change events; or
2. explicit official evidence that no relevant change occurred,

the effective-dated sector mapping remains:

`DATA_BLOCKED`

No current-only mapping may be used as historical PIT evidence.

## Acceptance criteria
For governed 2023+ research:
- TWSE annual event/no-change coverage = 100%
- TPEx annual event/no-change coverage = 100%
- current snapshot source health = PASS
- event-chain reconciliation = PASS
- unresolved chain mismatches = 0
- mapped PIT universe coverage >= 95%

Once those pass, W3A may feed the resulting intervals directly into:
- `src/sector_rs_replay.py`
- canonical Intraday PIT Replay
- W2 fail-closed validation

## Production impact
NONE.
