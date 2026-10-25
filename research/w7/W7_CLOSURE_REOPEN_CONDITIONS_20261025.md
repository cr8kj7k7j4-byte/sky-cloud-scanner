# W7 Closure / Reopen Conditions — 2026-10-25

> W7 external-intelligence workstream closure for the current inbound batch. No Production change.

## W5 adjudication consumed
- Overnight-to-First-30m Reversal — HOLD / PARTIAL DATA_BLOCKED
- Taiwan Dynamic Futures/ETF/Spot Lead-Lag — HOLD / PARTIAL DATA_BLOCKED
- Taiwan Broker-Identity / Skill-Conditioned Flow — HOLD / UNKNOWN HARD DATA GATE
- ACCEPT_FOR_PREREGISTRATION = 0

## W7 action
Pause new Alpha candidate intake from this research batch.
Do not create additional variants, thresholds, horizons, model families, ranking weights, or paid-data purchases merely to bypass Gate 0.

## Reopen triggers

### 1. Overnight-to-First-30m Reversal
Reopen W7/W5 evidence review only after:
- whole-universe synchronized intraday history materially improves toward the governed >=95% coverage gate;
- historical decision stream / deterministic all-candidate replay is available;
- effective-dated sector mapping and canonical outcome join are available;
- execution timestamp causality can be tested.

### 2. Dynamic Futures/ETF/Spot Lead-Lag
Reopen after:
- synchronized cross-market timestamp contract exists;
- stale-index handling is defined;
- auction/session alignment is defined;
- continuous-contract / roll handling is defined;
- downstream stock replay is no longer DATA_BLOCKED.

### 3. Broker-Identity / Skill-Conditioned Flow
Reopen only after:
- sample export or equivalent schema evidence is available;
- broker/branch lifecycle and effective-dated mapping are verified;
- licensing permits reproducible research;
- cost is justified relative to research value.

## Purchase policy
- Fugle: use existing/current capability first; no upgrade until an actual research bottleneck is demonstrated.
- TWSE broker-flow full-market package: DO_NOT_BUY NOW.
- TAIFEX paid tick/order data: do not buy before minute-level lead-lag evidence survives.
- Databento / other global high-frequency vendors: NOT_NEEDED for current Taiwan-core bottleneck.
- QuantConnect/LEAN: NOT_NEEDED as a new platform at this stage.

## W7 next operating mode
W7 remains in intelligence-monitoring mode only:
- watch for genuinely structural new data or execution architectures;
- immediately reject duplicates of frozen families;
- do not create research backlog while Gate 0 remains the dominant bottleneck.

## Formal status
RESEARCH_MORE

Reason:
The limiting factor is canonical PIT evidence/data architecture, not lack of additional strategy ideas.


## W0 Governance Update — 2026-10-26

W0/P0-G has formally resolved the v1.4 historical replay question:

- Historical full-rule replay for Sky Day Trading v1.4 is **NOT FULLY RECONSTRUCTABLE from the current GitHub SSOT**.
- Formal W2 status: **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**.
- Historical full-rule ablation must remain closed unless an authoritative `FROZEN_CANONICAL_IMPLEMENTATION` or `HISTORICAL_SNAPSHOT` is later supplied.
- No retrospective threshold/rule reconstruction is permitted.
- Production baseline remains unchanged.

### Updated system critical path
1. W4 — Forward Shadow/Paper evidence accumulation
2. P0-R — Portfolio/risk validation
3. W6 — Prospective execution/slippage/fill evidence
4. W3B — Reproducible forward evidence pipeline / operational hardening
5. W0/P0-G — Evidence review and governance
6. W2 — Future challenger validation only when provenance gates pass
7. W3A — PIT/data maintenance only; no synthetic v1.4 Alpha reconstruction
8. W5/W7 — Keep current inbound candidates HOLD until their data-specific blockers clear

### W7 action
Remain in low-intensity intelligence/vendor mode.
Do not generate more Alpha backlog while forward evidence and risk/execution validation are the dominant bottlenecks.

Reference:
- `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`
- GitHub Issue #122 — closed as GOVERNANCE_BLOCKED
