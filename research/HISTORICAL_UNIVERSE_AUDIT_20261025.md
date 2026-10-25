# Historical Universe / Survivorship Audit — 2026-10-25

## Scope
- Governed research window: 2023-01-01 onward
- Main-native live audit: GitHub Actions #40176911909
- Official data owner: src/official_universe_events.py on current main lineage

## Result
- Official sources healthy: 6 / 6
- Official events: 2,426
- Strict full-history intervals: 2,136
- Strict pre-window unresolved: 230
- Windowed intervals: 2,116
- Window unresolved: 0
- Left-censored at window start: 13
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

## Governance conclusion
- Historical membership differs materially from today's listed universe at every audited date.
- Promotion-grade research for 2023+ must use the point-in-time universe.
- Today's listing universe must not be used backward as a substitute.
- Full-history strict ledger still has 230 pre-window unresolved events; this PASS is not an all-history completeness claim.
