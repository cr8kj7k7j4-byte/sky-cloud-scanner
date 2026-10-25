# Historical Universe / Survivorship Audit — 2026-10-25

## Live audit result

Workflow: `40172934028`

### Fixed
- Corrected compact date handling so 8-digit Gregorian `YYYYMMDD` is no longer treated as ROC year + 1911.
- Historical PIT membership is now non-zero and plausible.
- Gate now fails closed when historical PIT membership is empty.
- Gate now requires actual delisting-source evidence.

### Measured PIT membership

| Date | PIT symbols |
|---|---:|
| 2023-12-31 | 1,786 |
| 2024-12-31 | 1,853 |
| 2025-12-31 | 1,930 |
| 2026-09-30 | 1,980 |

### Measured survivorship differences

2023-12-31:
- TWSE current 1,088 vs PIT 991
- TPEx current 892 vs PIT 795
- Current-only backward studies are therefore survivorship-biased.

2026-09-30:
- TWSE current 1,088 vs PIT 1,089
- TPEx current 892 vs PIT 891
- Membership still differs, so current-universe-only historical studies remain biased.

## Blocking issue

Historical Universe Gate = **FAIL**

Reason:
- `TWSE_DELIST` official source health = HTTP success but parsed_events = 0
- `TPEX_DELIST` official source health = HTTP success but parsed_events = 0
- The audit intentionally requires delisting evidence before promotion.

The TWSE official delisting page visibly contains historical termination records, so the remaining issue is an adapter / transport / parser mismatch rather than lack of official data.

## Governance decision

- Do not merge this branch into production yet.
- Do not claim survivorship control is complete.
- Any historical study built only from today's listing universe remains non-promotable.
- Next task: repair TWSE / TPEx delisting adapters, rerun live audit, then reassess the gate.
