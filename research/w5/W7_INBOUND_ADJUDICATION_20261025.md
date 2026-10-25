# W5｜W7 Inbound Candidate Adjudication — 2026-10-25

> Scope: Intake → Duplicate/Low-value Gate → PIT Feasibility → Pre-registration Decision.
> This document does not modify Production and does not authorize live trading.

## Governance references
- `SKY_SYSTEM_REGISTRY_V2_1.md`
- `research/RESEARCH_FREEZE_REGISTRY.md`
- `docs/SKY_VALIDATION_PROTOCOL_V1_0.md`
- `docs/SKY_V2_1_BASELINE_FREEZE_20261025.md`
- `docs/SKY_MASTER_CONTROL_STATUS_20261025.md`
- `docs/W3A_INTRADAY_PIT_REPLAY_STATUS_20261025.md`
- `research/w7/W7_VENDOR_DATA_DECISION_20261025.md`

## Latest W3A evidence incorporated

W3A status is now **ENGINEERING COMPLETE / DATA_BLOCKED**.

Verified existing 5m artifact:
- period: 2023-05-23 to 2026-10-22
- symbols: 100
- total bars: 2,704,785
- successful downloads: 100 / 100
- export validation: PASS
- but the sample is current-universe backward and carries survivorship bias

Maximum possible symbol coverage versus governed PIT Universe:
- 2023-12-31: 100 / 1,904 = 5.2521%
- 2024-12-31: 100 / 1,960 = 5.1020%
- 2025-12-31: 100 / 2,028 = 4.9310%
- 2026-09-30: 100 / 2,069 = 4.8333%

Required gate is >=95%, so the current 5m artifact is engineering/regression evidence only and cannot support promotion-grade PIT replay.

---

## 1. Overnight-to-First-30m Reversal for Taiwan

### Status
`HOLD`

### Hypothesis
隔夜資訊狀態可能在開盤後前 5/15/30 分鐘形成可測量的反向 repricing／residual-return 結構。

### Duplicate / Low-value Gate
PASS structural novelty.
- NOT P0-S 5m Breakout
- NOT Fixed-time Intraday Ranking
- NOT Weak-Regime Mean-Reversion
- NOT Event-driven Intraday Ranking
- NOT threshold / period / Top-N / weight / stop-target retuning

Structural difference:
- overnight state → opening repricing causal timing
- first-5/15/30m residual-return target family

### PIT Feasibility
**PARTIAL / DATA_BLOCKED**

Positive evidence:
- stock minute history exists from 2023-05-23
- 2023+ PIT Universe governance PASS
- replay builder / auditor / readiness gate / W2 fail-closed validator exist

Blocking evidence:
- whole-universe synchronized intraday history below required coverage
- historical decision stream / deterministic all-candidate replay missing
- effective-dated historical sector membership missing
- canonical outcome join missing
- empirical execution evidence missing

### Pre-registration Decision
**NOT YET ACCEPTED**

Gate 0 is not satisfied. The current 100-symbol artifact cannot be used to bypass survivorship and coverage requirements.

### Recommendation
Priority 1 after W3A external-data blockers are resolved.

---

## 2. Taiwan Dynamic Futures/ETF/Spot Lead-Lag State

### Status
`HOLD`

### Hypothesis
台指期、ETF、現貨間的資訊領先關係會隨市場狀態改變；同步 PIT lead-lag state 可能成為上游 market-intelligence / confirmation feature。

### Duplicate / Low-value Gate
PASS structural novelty.
- NOT Fixed-time Intraday Ranking
- NOT Event-driven Intraday Ranking
- NOT VNext Residual Ranking v1
- NOT Transparent Intraday ML
- if reduced to merely another ranking weight later → `REJECT_LOW_VALUE`

Structural difference:
- synchronized cross-market PIT data family
- dynamic lead-lag market-state architecture

### PIT Feasibility
**PARTIAL / DATA_BLOCKED**

Positive evidence:
- futures minute history exists from 2017-06
- stock/index minute history exists from 2023-05-23
- no paid tick data is required for first feasibility stage

Blocking evidence:
- synchronized whole-universe intraday history missing
- timestamp synchronization contract missing
- stale-index handling missing
- auction/session alignment missing
- continuous-contract / roll handling missing
- downstream canonical stock replay remains DATA_BLOCKED

### Pre-registration Decision
**NOT YET ACCEPTED**

Having minute bars does not establish execution timestamp causality. Gate 0 requires the cross-market timing contract first.

### Recommendation
Priority 2. W3A/W6 must establish synchronized timestamp/session/roll contract before re-review.

---

## 3. Taiwan Broker-Identity / Skill-Conditioned Flow

### Status
`HOLD`

### Hypothesis
券商／分點身分與 past-only 行為可能使相同買賣流具有不同資訊含量，對 1D–5D residual return 形成增量資訊。

### Duplicate / Low-value Gate
PASS structural novelty.
- NOT generic volume / RS
- NOT Event-driven Ranking
- NOT Transparent ML
- if reduced to a broker-score weight inside existing ranking → may become `REJECT_LOW_VALUE`

Structural difference:
- identity-tagged participant-flow data family
- past-only skill conditioning
- 1D–5D causal horizon rather than pretending the daily report is intraday

### PIT Feasibility
**UNKNOWN / HARD DATA GATE**

Observable facts:
- official TWSE full-market broker buy/sell daily report exists from 2012-10-25
- report is produced after close, so it cannot support same-day intraday causal use
- full-market excluding warrants internal-use list price: NT$80,000/month
- branch/self-trading aggregation caveats exist

Still unverified:
- sample export
- branch-code lifecycle
- historical effective-dated branch mapping
- schema stability
- licensing fit for reproducible research

### Pre-registration Decision
**NOT YET ACCEPTED**

### Recommendation
Priority 3. `DO_NOT_BUY NOW`; verify sample/schema/branch continuity/PIT mapping first.

---

# Final W5 Decision

| Candidate | Duplicate / Low-value | PIT feasibility | Pre-registration | W5 Status |
|---|---|---|---|---|
| Overnight-to-First-30m Reversal | PASS structural novelty | PARTIAL / DATA_BLOCKED | NOT YET | HOLD |
| Dynamic Futures/ETF/Spot Lead-Lag | PASS structural novelty | PARTIAL / DATA_BLOCKED | NOT YET | HOLD |
| Broker-Identity / Skill-Conditioned Flow | PASS structural novelty | UNKNOWN / HARD DATA GATE | NOT YET | HOLD |

## Current queue decision
- `ACCEPT_FOR_PREREGISTRATION`: **0**
- `HOLD`: **3**
- `REJECT_DUPLICATE`: **0**
- `REJECT_LOW_VALUE`: **0**
- `ARCHIVE`: **0**

## Priority order if blockers clear
1. Overnight-to-First-30m Reversal
2. Dynamic Futures/ETF/Spot Lead-Lag
3. Broker-Identity / Skill-Conditioned Flow

This is research-resource priority only, not a probability-of-profit or expected-return ranking.

## Production impact
NONE.
