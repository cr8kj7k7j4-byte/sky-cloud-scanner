# W0｜Sky Swing V1.0 Exact-Rule Governance Decision — 2026-10-26

- Authority: W0｜Sky 總控與版本治理 / P0-G
- Production baseline: **Sky Swing V1.0 — ACTIVE / unchanged**
- W1 state: **HOLD**
- Governance gate: **BLOCKED_EXACT_RULE_SPEC**
- Decision type: specification-governance debt; no trading-rule change

## 1. Decision

W0 determines that the current repository evidence is insufficient to reconstruct the exact executable Sky Swing V1.0 decision logic without inference.

Therefore:

1. Production remains Sky Swing V1.0 and is not modified.
2. No canonical replay may be labelled `Sky Swing V1.0` until an exact frozen rule specification is recovered or governed from contemporaneous pre-result evidence.
3. Existing 3-factor 5D / 3–20D Swing research remains evidence-only and must not be substituted for Production.
4. W1 remains HOLD even though canonical PIT data readiness is PASS.
5. No W4 Shadow/Paper handoff is authorized from historical proxy results.

## 2. Evidence reviewed

W0/W1 reviewed the current SSOT and historical repository evidence, including:

- `SKY_SYSTEM_REGISTRY_V2_1.md`
- `docs/SKY_MASTER_CONTROL_STATUS_20261025.md`
- `research/SKY_SWING_CANONICAL_PIT_REPLAY_PREREGISTRATION.md`
- `research/W1_SWING_VALIDATION_LAB_20261025.md`
- `research/W1_SWING_V1_EXACT_RULE_RECONSTRUCTION_GATE_20261026.md`
- current Swing research scripts and workflows
- PMS implementation and tests
- Git commit history containing Swing research
- Swing-named branches
- repository code search for FIXED_3R / MA20_TRAIL / SWING10_TRAIL
- issue / pull-request history mentioning Swing V1.0 / baseline

Result:

- ACTIVE baseline identity is documented.
- Complete executable Entry / Setup / Trigger / Stop / Exit definitions are not.
- Existing research scripts are later proxy/challenger implementations.
- PMS is a safety consumer of supplied levels and does not define the missing Production formulas.

## 3. Data layer status

The data blocker is resolved independently of this rule-spec blocker.

Latest valid W3/W1 evidence:

- canonical PIT unique symbols: 2,073
- price symbols available: 2,009
- symbol-day coverage: 95.83%
- 2023-12-31 coverage: 96.68% PASS
- 2024-12-31 coverage: 96.78% PASS
- 2025-12-31 coverage: 96.94% PASS
- 2026-09-30 coverage: 96.85% PASS
- duplicate rows: 0
- corporate-action conflicts: 0
- continuity conflicts: 0
- W1 readiness: READY_FOR_CANONICAL_SWING_REPLAY
- W3 → W1 handoff: PASS

Interpretation: **data is ready; strategy specification is not.**

## 4. Missing exact-rule fields

At minimum the following must be recovered or explicitly governed before canonical replay:

- Market Gate
- Trend rule
- Relative Strength rule
- Setup definition
- Trigger definition
- Anti-Chase rule
- RR Gate
- initial stop construction
- add rule
- FIXED_3R exact semantics
- MA20_TRAIL exact semantics
- SWING10_TRAIL exact semantics
- precedence when multiple exits fire
- max holding rule
- position sizing / max concurrent positions when part of the baseline
- decision-time / execution-time causality

## 5. Allowed unblocking evidence

Only evidence that predates visibility of the new canonical replay outcomes may define the frozen baseline:

1. pre-existing source code;
2. pre-existing versioned strategy document;
3. contemporaneous production configuration / decision log;
4. W0 reconstruction that cites contemporaneous evidence field-by-field and records unresolved ambiguities.

## 6. Forbidden

- no result-driven threshold fitting;
- no best-horizon selection;
- no stop/target tuning;
- no feature-weight tuning;
- no substitution of a research proxy for Production;
- no use of future/canonical outcomes to reconstruct a past rule.

## 7. Resume condition

When the exact-rule artifact exists, W1 resumes the preregistered sequence:

canonical replay → Train/Validation/OOS → >=3-fold Walk-forward → Bull/Neutral/Bear → 0.45%/0.65% cost stress → Exit comparison → Rule ablation → Feature ablation → Portfolio/Capacity → W1 final status.

Until then:

**Sky Swing V1.0 = ACTIVE / unchanged**

**W1 = HOLD / BLOCKED_EXACT_RULE_SPEC**
