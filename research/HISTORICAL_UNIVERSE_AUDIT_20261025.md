# Historical Universe / Survivorship Audit — 2026-10-25

## Scope

- Governed research window: 2023-01-01 onward
- Live audit workflow: GitHub Actions #40176306214
- Official sources:
  - TWSE_BASIC
  - TPEX_BASIC
  - TWSE_NEW
  - TPEX_NEW
  - TWSE_DELIST
  - TPEX_DELIST

## Result

- Official events: 2,499
- Strict full-history intervals: 2,201
- Strict pre-window unresolved: 163
- Windowed intervals: 2,116
- Window unresolved: 0
- Left-censored at window start: 10
- Continuous-listing annotations: 1
- Interval validation: PASS
- Historical source coverage: PASS
- Historical dates non-empty: PASS
- Historical Universe Gate: **PASS for 2023+**

## Current interval coverage

| Exchange | Current | Covered | Coverage |
|---|---:|---:|---:|
| TPEx | 892 | 892 | 100.0000% |
| TWSE | 1,088 | 1,087 | 99.9081% |

## PIT Universe

| Date | PIT symbols |
|---|---:|
| 2023-12-31 | 1,904 |
| 2024-12-31 | 1,960 |
| 2025-12-31 | 2,028 |
| 2026-09-30 | 2,069 |

## Survivorship evidence

Historical membership differs materially from today's universe at every audited date.
Therefore any 2023+ promotion-grade research must use the point-in-time universe rather than today's listing universe.

## Governance boundary

This PASS is scoped to the governed 2023+ research window.
The strict all-history ledger still contains 163 pre-window unresolved events and must not be described as complete all-history coverage.
