# W5 Intake — Taiwan Broker-Identity / Skill-Conditioned Flow

## Candidate
Taiwan Broker-Identity / Skill-Conditioned Flow

## Hypothesis
若可取得 point-in-time、無事後修正的券商／分點身份與交易流資料，部分身份條件化 flow 可能包含現有 Sky 價量與市場資訊之外的獨立資訊。

## Problem
補足目前 Sky 缺少 participant-identity / informed-flow 類資料的缺口。

## Market
Taiwan equities.

## Horizon
Intraday / short swing；尚未預註冊。

## Target / Label
尚未固定。不得以事後「哪個券商最準」作 label。

## Data source
需要歷史可重建且時間戳可信的 broker / branch identity flow data。若資料僅能事後取得或只提供 end-of-day aggregate，則 intraday hypothesis 不成立。

## Feature
候選：identity-conditioned net flow、persistence、cross-symbol skill stability、market-adjusted flow surprise。

## Trigger / Ranking
尚未固定。第一階段應先測 feature information content，不得直接做黑盒 ranking。

## Execution assumption
若資料不是在決策時點可得，必須 fail closed，不可用事後分點資料回填成假想即時訊號。

## Cost assumption
依股票策略至少 0.45% primary / 0.65% stress。

## Risk
- vendor / licensing
- historical PIT availability
- identity mapping instability
- survivorship / selection bias of “skilled” brokers
- multiple-testing / data snooping
- crowding and decay

## Structural Difference
屬新的 identity-tagged participant-flow data family，與現有 price/volume/event/residual families 有結構差異。

## Rejected-family difference
不直接等同 Event-driven Ranking 或 Transparent ML；但若只把「券商分數」加權進既有 ranking，則價值會顯著下降。

## Feasibility
- PIT：UNKNOWN / DATA HARD GATE
- Untouched OOS：理論可設計，前提是歷史資料完整
- After-cost test：可
- Portfolio/capacity：可
- Explainability：MEDIUM
- Complexity：MEDIUM–HIGH

## W5 Decision
Status：HOLD

Reason：
可能有高資訊增量，但目前最核心的資料來源、歷史 PIT、授權與取得成本均未確認。資料不可得時研究價值為零。

Next step：
W7 / W3A 先做 vendor/data feasibility。未證明 PIT 可得前，不進 Pre-registration、不購買資料。
