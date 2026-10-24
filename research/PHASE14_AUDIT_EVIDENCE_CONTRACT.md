# Sky 100 Phase 14｜Audit Trail + Decision Explainability + Evidence Ledger

## 目的
每一次買進、等待、觀察、加碼、減碼、停損、退出或禁止交易，都必須可以事後重建。

## Decision Audit Record
至少保存：
- decision_id
- symbol
- decision_time
- action
- decision_status
- Market State / Regime
- Strategy Version
- Model Version
- Feature Schema Version
- Rule Config Version
- Data Sources
- Evidence IDs
- Passed Gates
- Blocked Gates
- Risk Status
- Execution Status
- Rationale
- Input Fingerprint
- Record Fingerprint

## P0-K Evidence Ledger
每份證據至少保存：
- evidence_id
- source_type
- source_name
- source_uri
- published_at
- observed_at
- data_time
- credibility_tier
- content_digest
- claim
- fact_status

fact_status 只允許：
- OBSERVABLE_FACT
- ANALYTICAL_INFERENCE
- UNCONFIRMED

## Explainability
Explainability 只回答：
- 為什麼做這個動作
- 哪些 Gate 通過
- 哪個 Gate 否決
- 哪個風控/執行層狀態影響決策
- 使用哪些 Evidence 與版本

不得把 Explainability 當成因果證明，也不得宣稱決策一定正確。

## Audit Principle
沒有完整 Audit Trail 的交易或禁止交易，不得視為可治理的正式決策。
