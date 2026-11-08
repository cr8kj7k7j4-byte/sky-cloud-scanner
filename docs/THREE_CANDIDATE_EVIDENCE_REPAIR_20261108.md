# 三研究模型資料證據修復｜2026-11-08

本修復僅新增 **可執行、拒絕缺證據的資料檢查器**，未更動任何 Alpha 規則、Production 模型或自動下單。既有研究評估、成本及 W0/P0-G 18 gates 照舊。

## 執行

```bash
python -m unittest tests.test_three_candidate_evidence_gate
python -m research.three_candidate_evidence_gate data.json --output output/three_candidate_evidence.json
```

輸入 JSON 格式：`{"candidate":"REVENUE_MOM_5D","observations":[...]}`，依模型選擇 `REVENUE_MOM_5D`、`MCR`、`ETF_0050_TREND`。必備欄位由 `research/three_candidate_evidence_gate.py` 中 `FIELDS` 定義。所有時間戳均須使用含時區 ISO 8601。無資料、必要欄位缺漏、時序逆轉即 `INSUFFICIENT_DATA`，程序 exit 2。

## 必須接上的上游真實證據（本 PR 尚未接通）

- **Revenue MoM 5D**：官方 MOPS 原始公告識別碼、實際發布時刻（不得用法定截止日代理）、觀察時刻與決策時刻；歷史回補若不可得，即開始前瞻蒐集。2023–2026 歷史 PIT 0/87,588 不得自行改寫為已通過。
- **MCR**：原始來源須證明是個股層級的真實融資維持率。融資餘額變動不等於維持率；缺少真實個股維持率不宣稱低於130%。盤中買盤及成交應另以合法且實際有授權的即時資料驗證。
- **ETF 0050**：策略與同期買入持有均使用一致的配息、分割／調整與成本口徑，保留資料時間及樣本區間，另外執行嚴格的跨期間、獨立樣本外及成本壓力測試。此檢查器只檢查輸入證據，**不推論策略超額報酬或正期望**。

## 尚待端到端驗收
1. W3A 建立具憑證與資料時間標記的上游採集輸出，並留下 API/HTTP/來源、資料品質與缺值證據。
2. W1/W4/W6 接到既有模型的凍結版回測／前瞻事件 ledger；去重、驗證結果回填、有效成交與成本。
3. 在 GitHub Actions 中執行單元測試、真實資料驗證，附 run/log/artifact；CI 成功不代表資料充足。
4. >=200 獨立可評估樣本、>=20 未來交易日、>=2 市場環境、>=95% 結果完整、單一股票<=20%，W0/P0-G 才可考慮升級。

**狀態：RESEARCH_ONLY／INSUFFICIENT_DATA，不能宣稱 Production-ready。**
