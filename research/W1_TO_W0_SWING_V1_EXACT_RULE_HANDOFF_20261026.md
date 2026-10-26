# W1 → W0 Handoff｜Sky Swing V1.0 Exact-Rule Reconstruction

- Date: 2026-10-26
- From: W1｜Sky Swing 驗證實驗室
- To: W0｜Sky 總控與版本治理 / P0-G
- Priority: P0 validation blocker
- Production impact: NONE unless W0 separately governs a versioned specification

## 1. Current state

W3 canonical PIT daily data and W1 readiness are PASS. W1 is now blocked only because the active Production baseline `Sky Swing V1.0` is not reproducible from the current SSOT at rule level.

Formal W1 evidence:
- `research/W1_SWING_V1_EXACT_RULE_RECONSTRUCTION_GATE_20261026.md`
- `research/W1_SWING_VALIDATION_LAB_20261025.md`
- `research/SKY_SWING_CANONICAL_PIT_REPLAY_PREREGISTRATION.md`

## 2. W0 decision required

W0 should recover or govern one canonical, executable, versioned rule specification for the frozen baseline using only contemporaneous pre-result evidence.

Required fields:
- Market Gate
- Trend rule
- Relative Strength rule
- Setup
- Trigger
- Anti-Chase
- RR Gate
- initial stop formula
- add rule
- FIXED_3R semantics
- MA20_TRAIL semantics
- SWING10_TRAIL semantics
- multiple-exit precedence
- max holding constraint if any
- position sizing / max concurrent positions if part of baseline
- decision timestamp / execution timestamp causality

## 3. Allowed evidence

Only:
1. pre-existing source code;
2. pre-existing versioned strategy documents;
3. contemporaneous records predating the new canonical replay outcome;
4. explicit W0 reconstruction that documents every source and ambiguity.

## 4. Forbidden

- no new threshold fitting;
- no horizon selection from visible results;
- no proxy substitution;
- no stop/target tuning;
- no feature-weight tuning;
- no use of canonical replay outcomes to decide the reconstructed rule.

## 5. W1 resume condition

When W0 publishes a canonical versioned exact-rule artifact, W1 will resume automatically:

canonical replay → Train/Validation/OOS → >=3-fold Walk-forward → Bull/Neutral/Bear → 0.45%/0.65% cost stress → Exit comparison → Rule ablation → Feature ablation → Portfolio/Capacity → W1 final status.

Until then: **W1 HOLD / BLOCKED_EXACT_RULE_SPEC**.
