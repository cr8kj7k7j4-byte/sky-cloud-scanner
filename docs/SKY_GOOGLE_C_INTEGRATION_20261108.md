# Sky × Google C 方案｜2026-11-08 建置與驗收

## 已完成
- Google Sheets 已建立，位於使用者私人 Google Drive：
  https://docs.google.com/spreadsheets/d/1GL4LDXEweSqSTmLXe8mm9FIZawH_ICGSqq6fU1wC_xI/edit
- 試算表有「整合狀態」「股票日資料樣本」「API驗收紀錄」「系統與治理」四分頁。
- 從已驗證的 GitHub FinMind Run #42409566510（2330）與 #42409763691（6770）手動寫入日資料；已從 Google Connector 回讀確認寫入。
- 專用、唯讀研究資料的 Google Sheets publisher 位於 `research/finmind_to_google_sheets.py`。
- `tests/test_finmind_to_google_sheets.py` 驗證日期代碼一致性與失敗資料不會寫入。
- `.github/workflows/finmind-google-sheets-bridge.yml` 支援 PR 測試分支上的離線合約測試。只有未來 main 手動 dispatch 可執行外部同步，**沒有新增時間排程**。

## 未完成／限制
- Google Cloud Project、Cloud Run、Sheets API、Workload Identity Federation（WIF）尚未實際驗證。
- GitHub Actions 至 Google Sheets 的身份授權與遠端寫入尚未完成（不能把 Google Connector 權限視為 GitHub Actions 權限）。
- Google Drive 自動歸檔與完整歷史資料存放尚未建立。
- FinMind → Google Sheet 僅備妥程式；目前 Sheets 的內容為使用者授權下透過 Google Connector 手動寫入的「樣本」，不是即時自動同步。
- 既有 Sky Production 完全不改；三模型正期望、風控、全市場資料涵蓋仍各自待驗證。

## 最少需要的 Google Cloud 設定（不分享任何私鑰）
1. 確認有可使用的 Google Cloud Project、計費與預算告警。**未授權前不部署付費資源。**
2. 啟用 Google Sheets API、IAM Credentials API、Security Token Service API；如需 Cloud Run，另啟用 Cloud Run、Cloud Build 與 Artifact Registry。
3. 建立專用服務帳號及 GitHub Workload Identity Federation provider；限制 GitHub repository 與 branch/ref，最小權限。**不要產生或貼上 JSON key**。
4. 將服務帳號的電子郵件設為上述私人 Google Sheet 的編輯者；不要開啟公開共用。
5. 在 GitHub repo 設定三個 Actions **Variables**：
   - `GCP_WIF_PROVIDER`：完整 projects/NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER 名稱
   - `GCP_SHEETS_SERVICE_ACCOUNT`：服務帳號 email
   - `SKY_GOOGLE_SHEET_ID`：`1GL4LDXEweSqSTmLXe8mm9FIZawH_ICGSqq6fU1wC_xI`
   - 既有 `FINMIND_TOKEN` Secret 不需提供給對話。
6. 承接 PR 前先避免和 PR #306 的 `research/finmind_query.py` 重複變更。合併／整併後才執行手動 `FinMind to Google Sheets` 並驗證覆寫同一日期/代碼不會重複、API 記錄與手機讀取一致。
7. Google Cloud Run 須另外做部署、帳務、IAM、日誌、錯誤重試、回收與成本驗收；目前**未上線**，也不代表已有三模型訓練計算能力。

## 資料與交易護欄
- 日資料非即時報價。不得以 FinMind API 回傳 PASS 宣稱全市場資料完整或正期望。
- `research_only`、`overall=PASS`、股票代碼及資料日期一致才可同步。
- 同一股票＋日期只更新一行；重複既有鍵值超過一筆則失敗，不自動刪資料。
- Google Sheet 欄位為公開範例研究資料，非個人帳戶持倉；不存放 token 或券商憑證。
- 策略升版依 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`，仍需 W0/P0-G 治理。
