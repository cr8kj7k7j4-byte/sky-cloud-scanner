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

---

## 1. Overnight-to-First-30m Reversal for Taiwan

### Candidate
Overnight-to-First-30m Reversal for Taiwan

### Status
`HOLD`

### Hypothesis
隔夜資訊狀態可能在開盤後前 5/15/30 分鐘形成可測量的反向 repricing／residual-return 結構。

### Duplicate / Low-value Gate
- P0-S 5m Breakout：NOT DUPLICATE
- Fixed-time Intraday Ranking：NOT DUPLICATE
- Weak-Regime Mean-Reversion：NOT DUPLICATE
- Event-driven Intraday Ranking：NOT DUPLICATE
- 僅 threshold / period / Top-N / weight / stop-target 微調：NO

結構差異：
- 新 causal timing：overnight state → opening repricing
- 新 target family：first-5/15/30m residual return
- 不依賴既有 breakout/ranking 門檻微調

### PIT Feasibility
**PARTIAL / NOT YET PASS**

可觀察事實：
- Fugle 2023-05-23 起提供股票分鐘歷史資料。
- 2023+ PIT Universe 已 PASS。
- W3A replay builder、DQ、manifest、W2 fail-closed validator 已存在。
- Canonical Intraday PIT Historical Replay Dataset 仍為 `PARTIAL COMPLETE / DATA_BLOCKED`。

尚缺：
- promotion-grade historical decision snapshots
- 完整 market/sector context
- opening execution/slippage context
- frozen decision-time feature parity

### OOS
可設計，但 2026 已使用資料不得重新聲稱 fresh untouched OOS。真正 fresh OOS 必須保留未使用的後續期間。

### Pre-registration Decision
**NOT YET ACCEPTED**

理由：
資料來源層面已高度可行，但 canonical PIT replay 尚未 PASS。依 Gate 0，PIT / timestamp causality 未正式通過前不得進正式 Pre-registration 實驗。

### Recommendation
W3A replay dataset PASS 後，優先重新審查；三者之中這個 Candidate 的資料門檻最低、可解釋性最高。

---

## 2. Taiwan Dynamic Futures/ETF/Spot Lead-Lag State

### Candidate
Taiwan Dynamic Futures/ETF/Spot Lead-Lag State

### Status
`HOLD`

### Hypothesis
台指期、ETF、現貨間的資訊領先關係會隨市場狀態改變；若同步 PIT timestamp 可嚴格成立，lead-lag state 可作為 Market Intelligence / confirmation input。

### Duplicate / Low-value Gate
- Fixed-time Intraday Ranking：NOT DUPLICATE
- Event-driven Intraday Ranking：NOT DUPLICATE
- VNext Residual Ranking v1：NOT DUPLICATE
- Transparent Intraday ML：NOT DUPLICATE
- 僅新增一個 ranking weight：若最終如此，將降為 `REJECT_LOW_VALUE`

結構差異：
- 新 cross-market data family
- 新 synchronized PIT timing architecture
- 新 market-state formulation

### PIT Feasibility
**PARTIAL / NOT YET PASS**

可觀察事實：
- Fugle futures minute history 自 2017-06 起可用。
- 股票／ETF 分鐘歷史自 2023-05-23 起可用。
- 可先用分鐘資料測試，不需先購買 TAIFEX tick/order data。

尚缺：
- synchronized timestamp contract
- stale-index handling
- session / auction alignment
- continuous-contract / roll handling
- source innovation 必須嚴格早於 target observation
- downstream stock-side canonical replay context

### OOS
可保留，但須在同步資料契約固定後再鎖定期間。

### Pre-registration Decision
**NOT YET ACCEPTED**

理由：
資料看似可取得，但 cross-market causality 的核心不是「有分鐘 K」而是 clock synchronization、roll、session mapping 與 feature availability。Gate 0 尚未通過。

### Recommendation
先由 W3A/W6 建立 cross-market timestamp contract；若資料完整且無 leakage，再回 W5 轉 `ACCEPT_FOR_PREREGISTRATION`。

---

## 3. Taiwan Broker-Identity / Skill-Conditioned Flow

### Candidate
Taiwan Broker-Identity / Skill-Conditioned Flow

### Status
`HOLD`

### Hypothesis
券商／分點身分與 past-only 行為可能使相同買賣流具有不同資訊含量，對 1D–5D residual return 形成增量資訊。

### Duplicate / Low-value Gate
- Generic volume / RS：NOT DUPLICATE
- Event-driven Ranking：NOT DUPLICATE
- Transparent ML：NOT DUPLICATE
- 若最後只把「券商 skill 分數」加權進既有 ranking：可能 `REJECT_LOW_VALUE`

結構差異：
- 新 identity-tagged participant-flow data family
- 新 past-only skill conditioning
- horizon 先固定為 daily/short swing，而非假裝 intraday

### PIT Feasibility
**UNKNOWN / HARD DATA GATE**

可觀察事實：
- TWSE 官方 full-market broker buy/sell daily report 自 2012-10-25 起。
- 報表為盤後產製，適用 1D–5D，不適合作為同日 intraday causal signal。
- full-market excluding warrants 內部使用價格為 NT$80,000/月。
- 部分自營資料會彙總至總公司。
- 尚未確認 Sky 可取得 sample export、branch-code lifecycle、歷史 PIT mapping。

### OOS
理論可設計，但在資料 coverage / branch continuity 未證實前不可稱可執行。

### Pre-registration Decision
**NOT YET ACCEPTED**

理由：
PIT data contract、schema、branch continuity、license/cost 都尚未通過；現在購買資料會先承擔成本、再尋找 edge，違反 Sky 研究治理。

### Recommendation
`DO_NOT_BUY NOW`。只有在 sample/schema/branch continuity 驗證完成後，才可回 W5 重審。

---

# Final W5 Decision

| Candidate | Duplicate / Low-value | PIT feasibility | Pre-registration | W5 Status |
|---|---|---|---|---|
| Overnight-to-First-30m Reversal | PASS structural novelty | PARTIAL / DATA_BLOCKED | NOT YET | HOLD |
| Dynamic Futures/ETF/Spot Lead-Lag | PASS structural novelty | PARTIAL / sync contract missing | NOT YET | HOLD |
| Broker-Identity / Skill-Conditioned Flow | PASS structural novelty | UNKNOWN / hard data gate | NOT YET | HOLD |

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

The priority above is a research-resource ordering, not a probability of profit or expected return ranking.

## Production impact
NONE.
