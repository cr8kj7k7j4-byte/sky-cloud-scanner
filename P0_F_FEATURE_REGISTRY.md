# P0-F Feature Schema / Version Registry v1.1

Status: Production governance contract

## Objective
Every feature used by Sky must have an explicit identity and immutable semantic contract.
A feature name may not silently change formula, unit, source, lookback, timestamp boundary,
missing-value policy, normalization, or leakage characteristics.

## Required registry metadata per feature
- feature_id
- feature_name / name
- version
- description
- formula
- unit
- input source
- lookback
- timestamp semantics
- frequency
- missing policy
- normalization
- leakage risk
- owner
- deprecation status
- production status

## Required runtime lineage per feature snapshot
- symbol
- as_of
- calculation_timestamp
- available_at
- source
- feature schema version
- feature registry version
- feature_id
- feature version

`available_at` is the earliest timestamp at which the feature instance may legally be consumed.
It must never be backfilled with later revised data and then treated as historical PIT evidence.

## Version rule
Any semantic change requires a new feature version, including formula, benchmark, normalization,
missing policy, lookback, timestamp semantics, or source meaning.

## Current governed features
- momentum_1
- momentum_5
- volume_ratio
- vwap_distance_pct
- intraday_range_pct
- volatility_5
- relative_strength

## Leakage rule
Feature timestamps must reflect what was observable at as_of.
Future bars, unavailable end-of-day values, revised fundamentals not yet published,
and timestamp-misaligned market/stock inputs must never enter production features.

## Online / Offline parity rule
Research and Production must match on formula, version, timestamp logic, normalization,
missing policy, and universe. Any mismatch is `PARITY_FAIL`.

## Files
- Registry: src/feature_registry.py
- Store validation / runtime lineage: src/feature_store.py
- Parity gate: src/feature_parity.py
- Tests: tests/test_feature_registry.py, tests/test_feature_parity.py
- CI: .github/workflows/test-feature-registry.yml
