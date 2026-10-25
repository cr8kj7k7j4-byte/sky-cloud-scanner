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
8. CI:
   - .github/workflows/test-w3a-intraday-pit-replay.yml

## Builder outputs
- intraday_pit_replay.csv
- intraday_pit_replay_manifest.json
- intraday_pit_replay_gap_report.json

## Formal audits now implemented

### Coverage audit
Thresholds:
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
explicit OOS rows, and the W2 fail-closed replay contract PASS.

## Current actual readiness result

The code path is complete, but the repository still lacks promotion-grade historical source artifacts for:
- full historical candidate decision stream, not winners only;
- effective-dated historical sector mapping;
- complete market context at each decision timestamp;
- Phase / Anti-Chase feature snapshots;
- complete contemporaneous P0-O candidate pools and ranking context;
- execution context / spread-slippage evidence where genuinely available;
- canonical outcome join.

The 2023+ PIT Universe is already PASS and historical 5-minute export tooling exists.
Those two facts are not sufficient to reconstruct the entire decision-time state required by Issue #81.

Therefore:
- Coverage audit on the real canonical dataset: NOT_EVALUABLE
- Leakage audit on the real canonical dataset: NOT_EVALUABLE
- Timestamp causality audit on the real canonical dataset: NOT_EVALUABLE
- W2 readiness: DATA_BLOCKED
- W2 efficacy / 10-rule contribution analysis: NOT AUTHORIZED

## Highest-priority blocker
NO_EFFECTIVE_DATED_HISTORICAL_SECTOR_MAPPING

Next blockers:
1. NO_CANONICAL_HISTORICAL_DECISION_STREAM
2. NO_CANONICAL_OUTCOME_JOIN_INPUT
3. missing canonical market / feature / ranking / execution context inputs

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
