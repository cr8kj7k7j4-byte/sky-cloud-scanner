# Revenue Historical PIT Coverage Audit — 2026-10-25

## Scope

- Data universe: official monthly revenue history exported from MOPS historical revenue pages
- Markets: TWSE + TPEx
- Period: 2023-01 through 2026-09
- Audit workflow: GitHub Actions run `40168078271`
- PIT evidence requirement: `MOPS_OFFICIAL` + complete company-level `filing_published_at` + `point_in_time_verified=true`

## Result

| Year | Expected company-months | Covered | Coverage |
|---|---:|---:|---:|
| 2023 | 22,752 | 0 | 0.0000% |
| 2024 | 23,266 | 0 | 0.0000% |
| 2025 | 23,715 | 0 | 0.0000% |
| 2026 (Jan-Sep) | 17,855 | 0 | 0.0000% |
| **Total** | **87,588** | **0** | **0.0000%** |

Historical PIT Gate: **FAIL**

## Official-source discovery

1. MOPS forward endpoint `/mops/api/home_page/t51sb10` is live and verified.
2. The API exposes company-level latest publication records with company ID, company abbreviation, date, time, subject, and URL when records exist.
3. The official front-end calls `t51sb10` with only `count` and `marketKind`.
4. The probed official `moreInfoUrl` form exposed only `Stp` and `TK`; no year/month/date historical selector was found.
5. Therefore the current official interface does not provide a verified programmatic path to reconstruct complete 2023–2026 company-level publication timestamps.

## Governance conclusion

- Revenue MoM 5D: remain `PRE_PIT_CANDIDATE`.
- Revenue YoY Acceleration 5D: remain `PRE_PIT_CANDIDATE`.
- Do not run promotion-oriented Walk-forward using statutory-deadline proxy dates as if they were actual publication timestamps.
- Forward PIT collection continues and will create a prospectively valid research sample.
- Historical revenue values remain valid for descriptive research; the failure concerns knowledge-time alignment, not the revenue numbers themselves.
