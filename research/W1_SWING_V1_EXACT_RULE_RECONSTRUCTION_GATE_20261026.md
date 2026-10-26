# W1｜Sky Swing V1.0 Exact-Rule Reconstruction Gate

- Date: 2026-10-26
- Lab: W1｜Sky Swing 驗證實驗室
- Production baseline: **Sky Swing V1.0 — ACTIVE / unchanged**
- Gate status: **BLOCKED_EXACT_RULE_SPEC**
- Data readiness: **PASS**
- Promotion authority: W0 only

## 1. Why this gate exists

The canonical PIT daily dataset is now ready for promotion-grade Swing replay, but a replay is valid only if the exact frozen Production decision logic can be reproduced without inference.

The repository currently identifies `Sky Swing V1.0` as the active 3–20D long-only Production baseline, but does not contain a complete executable specification for all of:

- Market Gate
- Trend condition
- Relative Strength condition
- Setup definition
- Trigger definition
- Anti-Chase rule
- RR Gate
- initial stop construction
- add rule
- FIXED_3R exit implementation
- MA20_TRAIL exit implementation
- SWING10_TRAIL exit implementation
- exact precedence when multiple exits fire
- position sizing / max concurrent positions used by the frozen baseline

## 2. Evidence searched

W1 inspected:

- `SKY_SYSTEM_REGISTRY_V2_1.md`
- `docs/SKY_MASTER_CONTROL_STATUS_20261025.md`
- `research/SKY_SWING_CANONICAL_PIT_REPLAY_PREREGISTRATION.md`
- current Swing research scripts
- PMS code
- Git commit history containing Swing research
- Swing-named branches

Findings:

1. Registry confirms Swing V1.0 is ACTIVE.
2. Existing Swing research code is a later research proxy / challenger family, not an exact Production V1.0 implementation.
3. PMS enforces no stop-widening / no averaging-down and consumes supplied stop/target/add levels, but does not define the missing entry / setup / stop formulas.
4. No exact executable FIXED_3R / MA20_TRAIL / SWING10_TRAIL baseline implementation was found in the current SSOT.
5. Therefore a canonical replay cannot be claimed as Sky Swing V1.0 without inventing rules.

## 3. Prohibited substitutions

Until this gate is resolved, W1 must not:

- use the 3-factor 5D / 3–20D research proxy as Production V1.0;
- infer thresholds from screenshots, chat prose, or result-visible research;
- select 10D / 15D / 20D because they looked better historically;
- invent stop distance, target, MA20 trail timing, or Swing10 trail semantics;
- tune a rule after seeing canonical PIT outcomes.

## 4. Current valid evidence

Canonical W3/W1 data gate is PASS:

- PIT unique symbols: 2,073
- price symbols available: 2,009
- symbol-day coverage: 95.83%
- 2023-12-31 coverage: 96.68%
- 2024-12-31 coverage: 96.78%
- 2025-12-31 coverage: 96.94%
- 2026-09-30 coverage: 96.85%
- duplicate rows: 0
- corporate-action conflicts: 0
- continuity conflicts: 0
- W1 readiness: READY_FOR_CANONICAL_SWING_REPLAY

This proves the data layer is ready; it does not prove the strategy.

## 5. Required artifact to unblock

A single canonical executable rule specification must be recovered or governed before W1 can continue. It must state every decision-time input, formula, threshold, timestamp, precedence rule, stop rule and exit rule used by the frozen Production baseline.

Acceptable unblocking evidence:

1. pre-existing Production source code;
2. pre-existing governed strategy specification predating canonical replay results;
3. W0-approved reconstruction from contemporaneous version-controlled evidence.

Not acceptable:

- post-result reconstruction;
- new optimization;
- threshold fitting;
- best-performing horizon selection.

## 6. Resume sequence after unblock

Once exact-rule reproducibility is PASS:

1. canonical replay
2. Train / Validation / OOS
3. >=3-fold Walk-forward
4. Bull / Neutral / Bear
5. 0.45% / 0.65% cost stress
6. Exit comparison
7. Rule ablation
8. Feature ablation
9. Portfolio / concentration / capacity
10. W1 final status: PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE

## 7. W1 decision

**HOLD — BLOCKED_EXACT_RULE_SPEC**

Production remains unchanged. No W4 handoff is authorized from this gate alone.
