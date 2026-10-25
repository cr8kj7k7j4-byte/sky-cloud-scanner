# W5 Intake — Taiwan Dynamic Futures / ETF / Spot Lead-Lag State

## Candidate
Taiwan Dynamic Futures / ETF / Spot Lead-Lag State

## Hypothesis
期貨、ETF 與現貨之間的資訊領先關係可能隨市場狀態改變；動態 lead-lag state 若能以同步 PIT 資料事前辨識，可能提供 Sky 尚未具備的 cross-market information state。

## Problem
補足單一現貨市場訊號無法捕捉跨市場 price discovery 的缺口。

## Market
Taiwan equities + Taiwan index futures / relevant ETFs.

## Horizon
Intraday；具體 horizon 尚未預註冊。

## Target / Label
尚未固定。應避免先觀察哪個 horizon 最好再選擇。

## Data source
需要同步、具交易所時間戳且可歷史重建的：
- futures
- ETF
- spot/index
- PIT stock universe
- session calendar / roll handling

## Feature
候選：lead-lag coefficients、basis state、cross-market return innovations、lagged residual states。

## Trigger / Ranking
尚未固定。可能作為 Market State / Context feature，而非直接單檔買賣 trigger。

## Execution assumption
必須保證 feature timestamp 早於 stock decision timestamp；任何同步延遲、bar close look-ahead 都視為 Gate 0 fail。

## Cost assumption
股票端至少 0.45% primary / 0.65% stress；若涉及期貨或 ETF 實際交易，成本模型需分開建立。

## Risk
- timestamp misalignment / leakage
- futures roll / night-session handling
- false lead caused by asynchronous sampling
- high-frequency noise
- data vendor dependence

## Structural Difference
這是新的 cross-market PIT data family 與 market-state architecture，不是既有 Fixed-time Ranking / Event Ranking / Residual Ranking v1 的權重微調。

## Rejected-family difference
目前具明確結構差異。若最後只把 lead-lag 分數當成另一個 ranking weight，則可能降為 REJECT_LOW_VALUE。

## Feasibility
- PIT：UNKNOWN
- Untouched OOS：可設計
- After-cost test：可
- Portfolio/capacity：可
- Explainability：MEDIUM–HIGH
- Complexity：MEDIUM

## W5 Decision
Status：HOLD

Reason：
研究假設具獨立資訊價值，但同步 cross-market historical PIT data contract 尚未建立；在資料時間戳與 roll/session 規則未驗證前，不得進 Pre-registration。

Next step：
W3A / W6 先確認同步資料可取得性、timestamp contract、roll/session architecture，再回 W5。
