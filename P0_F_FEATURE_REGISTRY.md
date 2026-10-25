# P0-F Feature Schema / Version Registry v1.0

Status: Production governance contract

## Objective
Every feature used by Sky must have an explicit identity and immutable semantic contract.
A feature name may not silently change formula, unit, source, lookback, timestamp boundary,
missing-value policy, or leakage characteristics.

## Required metadata per feature
- name
- version
- description
- formula
- unit
- source
- lookback
- timestamp semantics
- missing policy
- leakage risk
- production status

## Version rule
Any semantic change requires a new feature version.
Examples:
- momentum_5 v1.0.0 cannot change from close_t / close_t-5 to a 30-minute VWAP momentum formula.
- relative_strength v1.0.0 cannot change its market benchmark while keeping the same version.

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
Future bars, end-of-day values unavailable intraday, revised fundamentals not yet published,
and timestamp-misaligned market/stock inputs must never enter production features.

## Files
- Registry: src/feature_registry.py
- Store validation: src/feature_store.py
- Tests: tests/test_feature_registry.py
- CI: .github/workflows/test-feature-registry.yml
