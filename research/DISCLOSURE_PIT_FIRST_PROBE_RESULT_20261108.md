# 2026-11-08 月營收與財報事件 PIT 首輪實跑驗收結果

## 結論
**INSUFFICIENT_DATA（正式歷史策略驗證仍不可用）**。
GitHub Actions Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42415830967
研究 PR: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/320

### 實際官方資料探針（2026-11-08 台灣時間約05:26）
- TWSE `https://openapi.twse.com.tw/v1/opendata/t187ap05_L`：HTTP 200，JSON 陣列，**1088筆**。
- TPEx `https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O`：HTTP 200，JSON 陣列，**893筆**。
- 合計 1,981 筆 **最新期彙總資料**（不得當作有 1,981 檔有效新交易事件）。
- 資料含「出表日期」「資料年月」「公司代號」「當月、上月及去年同期營收」等欄位；未見個別公司實際公開時間 `published_at`。
- **正確的結論是 API 可讀、部分資料結構已驗收；真實歷史逐公司公開時間沒有通過驗證**。出表日期與營收所屬月份均不得假冒各公司公告時間。
- 本次沒有向 MOPS 或第三方提供者實際證實歷史逐筆 `published_at`。不能將第一批上市／上櫃資料以某固定日期強制納入正式回測。

### 程式／驗證
- `research/disclosure_pit_gate.py` 與 `tests/test_disclosure_pit_gate.py`：8項測試全通過。
- 事件驗證需滿足 `published_at <= observed_at <= decision_at` 且時區／來源／時間精度齊全。
- 虛構/未經證實之模擬事件時間僅用於單元測試；即便通過格式檢查也標示 `source_authenticity_independently_verified=false`。
- 空輸入的正式數據門檻：合格歷史公告事件 **0**；不得宣稱已拿到 1,981 筆策略可評估事件。
- 本次沒有進行 Revenue MoM 5D 的歷史事件交易回測，也沒有財報盈餘公告的實際樣本驗證，沒有實際買賣訊號。

### 下一個阻塞與解法
1. W3A：檢索官方個股公告事件原文的可機器讀取資訊來源，必須逐筆有實際日期與時間，且可驗證 2023+ 歷史涵蓋率。
2. 如無法取得歷史檔案：使用 GitHub Actions 按適當時間收集新的官方原始資料及首次觀測時間，保留可審查的版本，但**第一次看到**不等於**實際公告**。
3. 使用已凍結 Revenue MoM 5D 研究，納入合格 PIT、上市櫃歷史母池、成本0.45/0.65%、真實可成交價、組合風險；前瞻樣本累計後再做 W0/P0-G 評估。
4. 尚不啟用財報事件正式策略，不修改 Production，也不新增無授權定時排程。

### 狀態區分
- 工程程式：已完成第一階段。
- 8項安全單元測試：PASS。
- 兩個官方最新月營收 API：PASS。
- 逐公司歷史公佈時間：FAIL / INSUFFICIENT_DATA。
- Revenue MoM 5D 完整 PIT、成本後穩定正期望：未驗證。
- Production：沒有修改。
