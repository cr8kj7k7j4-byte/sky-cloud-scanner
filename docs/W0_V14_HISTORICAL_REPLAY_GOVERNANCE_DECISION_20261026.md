# W0｜Day Trading v1.4 Historical Replay Governance Decision — 2026-10-26

## Decision

**Historical full-rule replay for Sky Day Trading v1.4 is formally classified as NOT FULLY RECONSTRUCTABLE from the current GitHub Single Source of Truth.**

This decision does **not** change the Production baseline.

Production remains:
- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP — ACTIVE
- Sky Swing V1.0 — ACTIVE

## Evidence reviewed

W0 reviewed the current canonical evidence chain:

- 2023+ PIT Universe Gate: PASS
- corrected whole-universe 5-minute raw market source: PASS
- TAIEX 5-minute benchmark: PASS
- objective PIT-safe decision-time primitives: reconstructable
- frozen-v1.4 source registry: 10 / 10 canonical W2 rule providers unresolved
- retained scheduled scanner artifacts: truncated Top-N / incomplete context
- Git history: conceptual A+ chain is documented, but canonical historical W2 rule outputs / thresholds are not preserved
- research-only P0-S 5m breakout: archived/rejected; cannot substitute
- Anti-Chase trigger-slip proxy: rejected as standalone hard gate; cannot substitute
- fail-closed evidence adapter: merged and active

Canonical evidence:
- `research/SKY_DAY_V14_FROZEN_RULE_SOURCE_REGISTRY.json`
- `research/frozen_v14_evidence_replay_adapter.py`
- `docs/W3A_INTRADAY_PIT_REPLAY_STATUS_20261025.md`
- GitHub Issue #117
- PR #116 / merge commit `0e072a52659fdfb0e1f14ec403dfb23baa6e5827`

## What is prohibited

W3A / W2 / any other workstream must **not**:

- invent missing v1.4 thresholds;
- infer historical gate booleans from later outcomes;
- substitute research-only strategy logic for Production v1.4;
- substitute archived/rejected 5m breakout logic;
- substitute current P0-C / P0-O / P0-X modules as if they were proven historical v1.4 providers;
- reconstruct missing Phase / MTF / Setup / Trigger / Anti-Chase states by retrospective optimization;
- report historical 10-rule contribution, expectancy uplift, or ablation efficacy as validated v1.4 evidence.

Any attempt to do so must fail closed.

## What remains valid

The following evidence remains valid and useful:

- PIT universe reconstruction;
- whole-universe intraday market data;
- market benchmark data;
- objective causal feature primitives;
- source lineage / coverage / leakage / survivorship audits;
- current Production behavior observation;
- forward Shadow/Paper evidence;
- execution / slippage evidence collected prospectively;
- P0-R portfolio/risk validation;
- current/future challenger validation under a fully frozen and preregistered rule contract.

## Forward validation path

Because the historical Production-v1.4 rule implementation is not fully reconstructable, the primary evidence path for the active Day Trading baseline becomes:

`Current Production Observation → Forward Shadow/Paper → Outcome Completion → Cost / Execution Evidence → Portfolio / P0-R → W0 / P0-G Review`

Minimum W4 forward-evidence gate remains:

- >=200 evaluable samples
- >=20 trading days
- >=2 market regimes
- outcome completeness >=95%
- single-symbol share <=20%
- portfolio / cost / capacity evidence
- P0-R gate
- P0-G review

This is forward evidence for **current behavior**, not retroactive proof of historical v1.4 profitability.

## W2 status

W2 remains available for:
- validation of future preregistered challengers;
- rule ablation where a fully frozen rule implementation exists;
- walk-forward / OOS / cost-stress / regime analysis on eligible datasets.

W2 must **not** continue waiting for a non-existent historical v1.4 source as if W3A can eventually synthesize it.

Formal W2 baseline status:

**HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**

This is a provenance limitation, not a profitability conclusion.

## Re-open condition

Historical v1.4 full-rule replay may be re-opened only if an authoritative external historical source is supplied and provenance-verified, such as:

- archived v1.4 source package;
- frozen rule/config bundle;
- complete historical decision snapshots;
- historical runner artifacts containing the canonical rule outputs;
- another source accepted by W0/P0-G as `FROZEN_CANONICAL_IMPLEMENTATION` or `HISTORICAL_SNAPSHOT`.

Until then, the historical full-rule replay lane is closed.

## Updated critical path

1. **W4 — Forward Shadow/Paper evidence accumulation**
2. **P0-R — Portfolio / risk validation**
3. **W6 — Execution/microstructure evidence supporting actual after-cost outcomes**
4. **W3B — Reproducible forward evidence pipeline / operational hardening**
5. **W0 / P0-G — Evidence review and governance decision**
6. W2 — future challenger validation only when eligible
7. W3A — maintain canonical data / PIT / lineage, no synthetic v1.4 Alpha reconstruction
8. W5/W7 — intake / low-intensity research only

## Production impact

**NONE.**

No Production rule, threshold, model, signal, position sizing rule, or live execution policy is changed by this governance decision.
