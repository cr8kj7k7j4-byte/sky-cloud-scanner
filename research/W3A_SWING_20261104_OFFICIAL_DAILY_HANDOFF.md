# W3A → W1｜2026-11-04 Official Swing Daily Raw History Handoff

## Authority / scope
- Owner: W3A/P0-DATA
- Strategy governance: W1 research / W0-P0-G Production authority
- Production changed: **NO**
- No trading action authorized.
- GitHub run: [41760932198](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41760932198)
- Artifact: `w3a-swing-official-delta-41760932198` (ID `13290506435`)
- Source baseline: repaired canonical W3 PIT daily history from [40252311345](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/40252311345).

## Verified
- Official 2026-11-03 current daily snapshot: 1,955 PIT-aligned common stocks; exact exchange date validated.
- Historical backfill: **6/6 actual open trading sessions successfully retrieved**, all from date-scoped official historical sources:
  - 2026-10-27: 1,959 PIT-aligned stocks
  - 2026-10-28: 1,958
  - 2026-10-29: 1,950
  - 2026-10-30: 1,957
  - 2026-11-02: 1,946
  - 2026-11-03: 1,955
- Missing eligible open sessions: **0**, within this requested interval.
- Market closures:
  - 2026-10-23: exceptional typhoon closure announced by TWSE and TPEx; contemporary [CNA report](https://www.cna.com.tw/news/afe/202610220388.aspx).
  - 2026-10-24/25, 10-31, 11-01: nontrading weekend/holiday.
  - 2026-10-26: exchange calendar replacement holiday.
- Parser/market calendar tests: **14 passed**.
- CI status: **SUCCESS**.
- Dated sources: TWSE `MI_INDEX?date=YYYYMMDD&type=ALLBUT0999`, TPEx `otc_quotes_no1430/stk_wn1430_result.php?d=ROC/MM/DD`.
- Explicitly **reject** TPEx `daily_close_quotes` for dated backfill: a 2026-10-30 request returned the latest 2026-11-03 dataset.
- No prior-close/open/bid/ask synthesis, no current-membership substitution. Each row validated against canonical PIT intervals and audited with SHA-256.

## Classification
`RAW_DATA_FETCHED_CA_PENDING`, **NOT `READY_FOR_W1_CANONICAL_SWING_REPLAY` for a refreshed 2026-11-03 dataset**.

The W3 base data previously passed the older registered 2023+ price-coverage gate. This run repairs the *raw last-six-open-sessions gap*, **not** the corporate-action-adjusted historical series. It must not be used directly to generate new V1.1 execution signals without:
1. Official corporate-action event evidence (ex-rights, ex-dividends, reductions, splits) for the new 2026-10-27..11-03 range with point-in-time ratios and continuity audit.
2. Per-symbol append preserving source/as-of, PIT exchange, duplicate/date checks, and no future data leakage.
3. Re-run the W1 readiness + freshness gates against the **updated combined artifact**, not the frozen old artifact.
4. Scheduled run and artifact retrieval evidence before claiming ongoing automatic daily updates.

## Intraday incident (independent)
- 2026-11-04 09:51 scanner: only **86/1,985 = 4.33%** verified last-traded MIS quote coverage; both markets' opening pools were available, but most `z` prices were missing.
- Fugle bulk snapshot plan-restricted (403); no supported authorized full-market alternative proved.
- [PR #229](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/229) tests passed: fail-close candidate publication *before* normal Telegram output; **does not restore missing quotes**.
- [PR #232](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/232) tests passed: stale V1.1 signal-date must fail workflow, not appear as green operational readiness.

## Governance
- Keep PRs draft until reviewed; W1–W7 may not independently change Production.
- Sky Swing V1.0 and Day Trading v1.4 remain Production.
- This is engineering/data evidence, not strategy profitability, trading eligibility, or a Production upgrade.
