# W3A｜Intraday PIT Historical Replay Dataset — Build & Audit Status 2026-10-25

## Current status
**ENGINEERING COMPLETE / DATA_BLOCKED**

Issue #81 engineering scope has been implemented without changing Production trading logic.

## Completed engineering
1. Canonical W2 replay contract:
   - research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md
2. W2 fail-closed validator:
   - research/intraday_replay_validator.py
3. W2 validation runner:
   - research/w2_intraday_validation_runner.py
4. 2023+ PIT historical universe gate:
   - PASS
5. Canonical replay builder:
   - research/build_intraday_pit_replay.py
6. Formal replay auditor:
   - research/audit_intraday_pit_replay.py
7. Source readiness gate:
   - research/intraday_pit_replay_readiness.py
8. Existing 5m source coverage audit:
   - research/INTRADAY_5M_SOURCE_COVERAGE_AUDIT_20261025.json
9. CI:
   - .github/workflows/test-w3a-intraday-pit-replay.yml

## Formal audits implemented

### Coverage audit
Required:
- PIT Universe >= 95%
- Market Context >= 95%
- Sector Mapping >= 95%
- Sector RS / price context >= 95%
- Phase / Anti-Chase >= 95%
- Outcome completeness >= 95%
- net_r_045 completeness = 100%
- net_r_065 completeness = 100%

### Leakage audit
Fail conditions include:
- feature cutoff later than decision timestamp
- outcome timestamp earlier than decision timestamp
- outcome fields referenced by decision-time features
- future-dated sector mapping
- UNKNOWN / MISSING spread imputed as zero

### Timestamp causality audit
Required:
- feature_cutoff_timestamp <= decision_timestamp
- zero violations

### W2 readiness gate
Requires all formal coverage thresholds, leakage PASS, timestamp causality PASS,
explicit OOS rows, and W2 fail-closed replay contract PASS.

## Existing 5m artifact audit

Verified GitHub Actions evidence:
- workflow run: 39963770301
- artifact ID: 12506631305
- artifact: sky-history-5m-39963770301
- artifact digest: sha256:3e3c820987242db7119ddc104b777916fa5cf63908afeff8c440091a1da99cd1
- period: 2023-05-23 to 2026-10-22
- symbols: 100
- total 5m bars: 2,704,785
- successful downloads: 100 / 100
- export validation: PASS
- universe method: deterministic SHA256 sample from the current official TWSE/TPEx universe
- artifact manifest warning: current-universe backward sampling has survivorship bias

Maximum possible symbol coverage versus governed PIT Universe:
- 2023-12-31: 100 / 1,904 = 5.2521%
- 2024-12-31: 100 / 1,960 = 5.1020%
- 2025-12-31: 100 / 2,028 = 4.9310%
- 2026-09-30: 100 / 2,069 = 4.8333%

The required gate is >=95%. Therefore this artifact is valid for engineering/regression/diagnostic use only and is **not promotion-grade canonical replay evidence**.

## Current real-data audit result

The code path is complete, but the repository / authorized artifacts do not yet contain a promotion-grade canonical historical replay dataset.

Therefore:
- 2023+ PIT Universe governance: PASS
- Existing 100-symbol 5m export integrity: PASS
- Whole-universe 5m source coverage: FAIL
- Coverage audit on a real canonical replay dataset: NOT_EVALUABLE
- Leakage audit on a real canonical replay dataset: NOT_EVALUABLE
- Timestamp causality audit on a real canonical replay dataset: NOT_EVALUABLE
- W2 readiness: DATA_BLOCKED
- W2 efficacy / 10-rule contribution analysis: NOT AUTHORIZED

## External-data blockers

Highest priority:
1. EXTERNAL_DATA_REQUIRED:EFFECTIVE_DATED_HISTORICAL_SECTOR_MEMBERSHIP

Then:
2. EXTERNAL_DATA_REQUIRED:SYNCHRONIZED_WHOLE_UNIVERSE_INTRADAY_HISTORY
3. EXTERNAL_DATA_REQUIRED:HISTORICAL_DECISION_STREAM_OR_DETERMINISTIC_ALL_CANDIDATE_REPLAY
4. EXTERNAL_DATA_REQUIRED:CANONICAL_OUTCOME_JOIN
5. EXTERNAL_DATA_REQUIRED:EMPIRICAL_EXECUTION_EVIDENCE

Additional missing canonical inputs:
- market context snapshots
- feature / Phase / Anti-Chase snapshots
- complete ranking candidate-pool context

No proxy may be substituted for promotion-grade evidence.

## Machine-executable flow

Build:
python research/build_intraday_pit_replay.py --decisions <decision_snapshot.csv> --pit-universe <pit_universe_intervals.json> --out-dir research_output/w3a_intraday_pit

Audit:
python research/audit_intraday_pit_replay.py --dataset research_output/w3a_intraday_pit/intraday_pit_replay.csv --out research_output/w3a_intraday_pit/audit.json --audited-dataset-out research_output/w3a_intraday_pit/intraday_pit_replay_audited.csv

W2 only if audit gate = PASS:
python research/w2_intraday_validation_runner.py --dataset research_output/w3a_intraday_pit/intraday_pit_replay_audited.csv

## Production impact
NONE.

Sky Day Trading v1.4 / P0-C MVP remains the Production baseline.
