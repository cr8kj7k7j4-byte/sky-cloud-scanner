# W5 Intake — Overnight-to-First-30m Reversal for Taiwan

## Candidate
Overnight-to-First-30m Reversal for Taiwan

## Hypothesis
隔夜資訊與開盤失衡可能在台股開盤後前 30 分鐘產生可測量、可反轉或均值回歸的短期報酬結構；研究目標不是重做一般弱勢均值回歸，而是測試「隔夜狀態 → 開盤後固定早盤窗口」的條件式反應。

## Problem
補足 Sky 對 overnight information state 與開盤初期價格反應的結構性研究缺口。

## Market
Taiwan equities.

## Horizon
Overnight close-to-open state；execution horizon = open to first 30 minutes.

## Target / Label
尚未預註冊。候選方向應以 open-to-30m forward return / residual return 為主，不得先看結果再選 label。

## Data source
需要：
- 前一交易日收盤
- 當日開盤
- 開盤後至少 1m / 5m PIT bars
- PIT universe
- corporate action continuity

## Feature
候選可包含 overnight gap、market/sector overnight state、open imbalance proxies；正式 feature list 尚未固定。

## Trigger / Ranking
未固定。不得直接沿用 Fixed-time Intraday Ranking 的 Top-N / threshold 架構作局部調參。

## Execution assumption
開盤後因價差、滑價、撮合品質與 volatility 較高，必須由 W6 / W2 使用 execution-adjusted cost assumptions 驗證。

## Cost assumption
最低遵守 0.45% round-trip primary / 0.65% stress；開盤窗口應額外檢查更高滑價敏感度。

## Risk
- 開盤滑價與 spread
- overnight news gap tail risk
- 交易量集中
- 反轉訊號可能只是 microstructure artifact
- 與既有 intraday reversal family 的重疊風險

## Structural Difference
與 Weak-Regime Mean-Reversion 的差異：新 target timing（overnight state → first-30m reaction），不是 MA/holding-period retuning。
與 Fixed-time Intraday Ranking 的差異：核心 hypothesis 是隔夜資訊狀態及開盤 reaction，而非純固定時間橫斷面排名。

## Rejected-family difference
目前存在可辯護的結構差異，但仍需 pre-registration 明確固定 target / causal timing 才能避免落回已凍結家族。

## Feasibility
- PIT：UNKNOWN / BLOCKED BY CANONICAL INTRADAY PIT DATASET READINESS
- Untouched OOS：可設計，但 2026 已使用資料不得稱 fresh OOS
- After-cost test：可
- Portfolio/capacity：可
- Explainability：HIGH
- Complexity：LOW–MEDIUM

## W5 Decision
Status：HOLD

Reason：
有結構差異與合理市場機制，但正式 Intraday PIT Historical Replay Dataset 尚未完成，且 target / label 未預註冊。不得先回測後再選反轉定義。

Next step：
W3A 完成 canonical intraday PIT replay dataset 後，若仍能保留 untouched OOS，才評估 ACCEPT_FOR_PREREGISTRATION。
