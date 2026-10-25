# W3A｜Issue #81 Intraday PIT Historical Replay Dataset — Status 2026-10-25

## Scope
Owner: W3A｜Sky Data & Feature Engineering

Issue: #81 W3: build canonical Intraday PIT Historical Replay Dataset for W2 validation

Production impact: NONE. Sky Day Trading v1.4 / P0-C MVP remains unchanged.

## Delivered engineering components
1. research/intraday_pit_replay_builder.py
   - canonical row assembly
   - PIT universe membership attachment
   - decision-time context joins
   - outcome join only after feature freeze
   - versioned manifest

2. research/intraday_pit_replay_audit.py
   - formal coverage audit
   - leakage audit
   - timestamp causality audit
   - unknown spread zero-imputation detection
   - future sector mapping detection
   - W2 fail-closed contract validation
   - leakage status can be promoted to PASS only after the audit itself passes

3. research/intraday_pit_replay_readiness.py
   - source-artifact inventory
   - fail-closed DATA_BLOCKED result when promotion-grade source domains are absent

4. CI: .github/workflows/w3a-intraday-pit-replay.yml

## Formal gate
W2 may run canonical 10-rule efficacy only when all pass:
- PIT Universe >= 95%
- Market Context >= 95%
- Sector Mapping >= 95%
- Sector RS / price context >= 95%
- Core Phase / Anti-Chase >= 95%
- Outcome completeness >= 95%
- Cost 0.45% completeness = 100%
- Cost 0.65% completeness = 100%
- Leakage audit = PASS
- Timestamp causality violations = 0
- OOS rows explicitly present
- W2 replay validator = PASS

Any failure => DATA_BLOCKED.

## Current source-readiness expectation
The repository currently contains governed 2023+ PIT Universe infrastructure, W2 replay contract / validator, and historical 5m export tooling.

The repository does not currently contain committed promotion-grade canonical inputs for the full historical decision stream, effective-dated historical sector mapping, complete contemporaneous market/sector/feature/ranking/execution contexts, and canonical outcome join.

Therefore the current readiness gate is expected to fail closed until those source artifacts are actually supplied or reproducibly generated.

This is a data availability result, not a strategy result.
