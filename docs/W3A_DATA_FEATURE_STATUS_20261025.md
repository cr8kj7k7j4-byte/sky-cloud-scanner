# W3A Data & Feature Engineering Status — 2026-10-25

## DATA STATUS
WARN

- 2023+ Point-in-Time Universe gate is PASS.
- Standardized Dataset DQ contract has been added in this branch.
- Canonical Intraday PIT Historical Replay Dataset remains incomplete.

## FEATURE STATUS
WARN

- Feature Registry upgraded to include stable feature_id, frequency, normalization, owner and deprecation status.
- Feature snapshots now carry calculation_timestamp and available_at.
- Online/Offline parity gate added for formula, version, timestamp semantics, normalization, missing policy and universe.

## PIT STATUS
PARTIAL PASS / BLOCKED

- Historical Universe 2023+ = PASS.
- Revenue historical verified filing timestamp coverage remains 0.0000% and BLOCKED.
- Statutory deadline proxies remain prohibited as verified PIT timestamps.

## DQ STATUS
WARN

Standard output schema:
- Coverage
- Freshness
- Completeness
- Duplicates
- Timestamp Integrity
- Source Health
- Status

Allowed status:
PASS / WARN / FAIL / BLOCKED

## BLOCKERS
1. Canonical Intraday PIT Historical Replay Dataset is not yet complete.
2. Historical verified Revenue filing_published_at coverage remains unavailable.
3. Actual Research-vs-Production parity must be run against concrete online/offline feature configurations.

## NEXT PRIORITY
1. Wire standardized DQ reports into each replay input dataset.
2. Build canonical Intraday PIT Replay rows from PIT universe + market/sector/stock/execution context.
3. Run W2 fail-closed validator.
4. Keep strategy logic frozen; no P0-C changes from W3A.
