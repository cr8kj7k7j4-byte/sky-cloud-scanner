# Sky Validation Protocol V1.0

> 目的：把「看起來有效」轉成「有可重複證據支持」。任何研究策略均適用。

## Gate 0 — Data Integrity
必須通過：
- Point-in-time alignment
- Survivorship bias audit
- Look-ahead / leakage audit
- Corporate action / symbol continuity
- Feature timestamp contract
- Missing-data policy
- Execution timestamp causality

Fail = STOP。不得以漂亮回測結果覆蓋資料缺陷。

## Gate 1 — Pre-registration
研究開始前固定：
- Universe
- Horizon
- Entry / Trigger
- Stop / Target / Exit
- Cost model
- Feature list
- Ranking rule
- Market Regime rule
- Portfolio constraints
- Promotion thresholds

結果出來後不得用局部閾值搜尋救模型。

## Gate 2 — Train / Validation / OOS
最低要求：
- Train、Validation、OOS 明確分離。
- OOS 不得被用來反覆調參。
- 已使用過的 2026 資料不得重新稱為 fresh OOS。

## Gate 3 — Walk-forward
至少 3 folds，追蹤：
- Expectancy
- PF
- Win rate
- Avg Win / Avg Loss
- MAE / MFE
- Max Drawdown
- Sample count
- Turnover

## Gate 4 — Regime Stability
至少檢查：
- Bull
- Neutral
- Bear

不得因總體績效正值而掩蓋某 Regime 災難性失效。

## Gate 5 — Cost / Slippage Stress
正式比較：
- 0.45% primary round-trip cost
- 0.65% stress cost

若策略只能在零成本或極低成本下成立，不得升版。

## Gate 6 — Rule / Feature Ablation
對 Market Gate、Sector/RS、Anti-Chase、Phase、Setup、Trigger、RR Gate 做 Remove-One 測試。

目標不是保留最多規則，而是確認每條規則是否：
- 提升 after-cost Expectancy；
- 降低 DD；
- 跨 fold / regime 穩定；
- 或至少具明確風控價值。

## Gate 7 — Portfolio / Capacity
最低檢查：
- Max concurrent positions
- Position sizing / 1R
- Correlation
- Sector concentration
- Single-symbol concentration
- Capacity / liquidity
- Portfolio heat
- Max DD
- Kill Switch

## Gate 8 — Shadow / Paper
最低候選 Sufficiency Gate：
- >= 200 可評估樣本
- >= 20 交易日
- >= 2 Market Regime
- Outcome completeness >= 95%
- Single-symbol share <= 20%

Counterfactual outcome 不得描述為真實成交或真實損益。

## Gate 9 — Small Live
只在 Gate 0–8 全部通過後啟動，小額與固定 1R。
需追蹤：
- Fill rate
- Slippage
- Missed trades
- Reject reasons
- Live vs backtest expectancy delta
- Live MAE / MFE
- Operational errors

## Gate 10 — Production Promotion
P0-G 僅在全部 Gate 通過後可將 Challenger 升為 Champion。

任何一項重大 Gate 失敗：
- Candidate → HOLD / REJECTED / ARCHIVED
- 不得用主觀信心補足證據。

## 核心判斷指標
首要：After-cost Expectancy、PF、Max Drawdown、Stability。
Win Rate 僅為輔助，不是單獨升版依據。

## 系統成功定義
「穩定」不等於每天獲利；穩定代表 Edge 在合理樣本、不同時間與市場環境下仍可重複，且虧損與回撤可被 P0-R 約束。


## Legacy Production Replay Limitation — 2026-10-26

A historical Production baseline may be evaluated with full rule-ablation claims only when its historical rule implementation is provenance-verifiable.

If a legacy baseline lacks authoritative frozen rule/config/decision sources:

- do not reconstruct missing rule thresholds retrospectively;
- do not substitute a research-only or archived strategy;
- do not infer gate booleans from outcomes;
- do not report historical rule contribution / ablation as validated evidence.

Allowed fallback evidence path:

`Current Production Observation → Forward Shadow/Paper → Outcome Completion → Cost/Execution Evidence → Portfolio/P0-R → P0-G`

This fallback validates current forward behavior only. It does not retroactively prove the historical baseline's past expectancy or rule efficacy.

For Sky Day Trading v1.4, the formal governance status is:
`HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE`

See:
`docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`
