# W1 → W3 Handoff｜Sky Swing Canonical PIT Historical Price Blocker

- Date: 2026-10-25
- Owner of requirement: W1｜Sky Swing 驗證實驗室
- Requested implementation owner: W3｜Sky 資料與系統工程 / P0-DATA
- Production baseline affected: **NONE**
- W1 status: **HOLD**
- Priority: P0 validation blocker

## 1. Problem statement

The canonical 2023+ point-in-time universe layer now passes and persists actual membership intervals.

Latest evidence:
- Historical Universe workflow run: `40193567617`
- Canonical intervals: **2,116**
- interval validation: PASS
- unresolved events in governed window: 0

However the existing Swing historical price artifact contains only 100 symbols selected from a current listing universe.

W1 readiness run `40193629353` measured actual PIT price coverage:

| Date | PIT N | Covered | Coverage |
|---|---:|---:|---:|
| 2023-12-31 | 1,869 | 88 | 4.71% |
| 2024-12-31 | 1,925 | 90 | 4.68% |
| 2025-12-31 | 1,993 | 96 | 4.82% |
| 2026-09-30 | 2,035 | 99 | 4.86% |

Registered W1 readiness threshold: **>=95%**.

Therefore canonical Exit / Rule Ablation / Feature Ablation / Portfolio validation is blocked.

## 2. Required dataset

A governed 2023-01-01+ daily OHLCV history for symbols that are eligible under `pit_intervals.json`.

Minimum fields:
- symbol
- exchange
- trading_date
- open
- high
- low
- close
- volume
- turnover when available
- adjusted flag / adjustment method
- source
- source_as_of / retrieved_at

Recommended metadata:
- listed_from / listed_to interval identity
- source request range
- data schema version
- checksum / artifact digest
- missing-range reason
- quality status

## 3. Corporate-action requirement

For core 3–20D Swing research, prefer a corporate-action-aware adjusted daily series.

Do not:
- silently splice unadjusted series across splits / capital reductions;
- forward-fill prices over suspended / unlisted periods;
- infer unknown corporate actions;
- use current listing status to determine historical eligibility.

## 4. PIT join rule

For each trading date D:

1. Determine eligible symbols from canonical PIT intervals.
2. Join price data only for eligible membership.
3. Record missing eligible symbols separately.
4. Do not replace missing historical names with current names.
5. Preserve TWSE / TPEx market-transfer interval identity.

## 5. Coverage gate

W1 will rerun `research/validate_swing_pit_readiness.py`.

Minimum registered gate:
- >=95% price-history coverage at all registered audit dates.

A coverage PASS is necessary but not sufficient; W1 will separately test missingness concentration and material bias before promotion-grade replay.

## 6. Granularity

Daily data is sufficient for the core Sky Swing 3–20D canonical replay unless an active frozen rule requires intraday state.

Do not collect full-market 5-minute history merely to satisfy the daily Swing validation need.

Intraday data should remain a separate requirement for rules that explicitly use VWAP / intraday trigger quality / spread / breakout-bar structure.

## 7. Candidate source capability

Fugle Historical Candles supports:
- daily timeframe `D`;
- individual stock history back to 2010 for listed / OTC equities;
- date windows shorter than one year per request;
- adjusted daily/weekly/monthly data via `adjusted=true`.

W3 must still validate API entitlement, rate limits, reproducibility, storage, retries and source metadata before adopting it as the governed implementation.

## 8. Acceptance criteria for W1

W3 handoff is accepted by W1 only when:

- canonical PIT intervals are consumed rather than today's universe;
- adjusted daily OHLCV is available for the governed window;
- >=95% PIT coverage gate passes on all audit dates;
- missingness report is generated;
- duplicate / symbol-continuity conflicts are zero or explicitly quarantined;
- artifact is reproducible and versioned;
- retrieval and source timestamps are preserved;
- W1 can consume the artifact without rebuilding membership logic.

## 9. W1 resume point

After acceptance, W1 resumes automatically from the frozen contract:

1. canonical replay
2. Train / Validation / OOS
3. >=3-fold Walk-forward
4. Bull / Neutral / Bear
5. 0.45% / 0.65% costs
6. Exit comparison
7. Rule ablation
8. Feature ablation
9. Portfolio / concentration / capacity
10. final W1 status for W0

No retuning is authorized during the handoff.


## 10. Machine-to-machine handoff

To remove the need for manual W1 re-entry, W3 should publish the governed daily dataset as a GitHub Actions artifact and then emit:

- event type: `w3_swing_data_ready`
- `client_payload.run_id`: W3 workflow run id that owns the artifact
- `client_payload.artifact_name`: exact artifact name

Canonical per-symbol files for this interface use the suffix `*_D.json`. The existing W1 readiness validator also accepts legacy `*_5.json` only for gap measurement; W3 canonical delivery should use daily files.

W1 listener:
- `.github/workflows/w1-swing-w3-data-handoff.yml`

The listener:
1. rebuilds the official PIT membership intervals;
2. downloads the exact W3 artifact;
3. runs the registered >=95% readiness gate;
4. fails closed unless status is `READY_FOR_CANONICAL_SWING_REPLAY`;
5. preserves the acceptance evidence as a 90-day artifact.

This interface does not authorize any strategy retuning or Production change.
