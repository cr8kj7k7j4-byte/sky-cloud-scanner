# 官方公告逐筆事件帳本與富果回溯資格｜2026-11-08

**狀態：ENGINEERING_PILOT_PASS / GCS_E2E_NOT_VERIFIED / EVENT_PIT_INSUFFICIENT_DATA。**

## 目的與相依性
- PR #322 已實際取得四個 TWSE、TPEx 公開來源原始快照（非富果付費行情）。
- PR #326 為堆疊 GCS「只新增物件、逐 byte 讀回」功能；五項單元測試通過，但 GitHub 工作流程在 PR 模式不做真正雲端上傳，因此不可宣稱 GCS 成功。
- 本 PR #329 新增 provisional event ledger、去重/修訂與富果事件回溯前置條件。**先完成本地與官方來源實跑，不代表歷史公告時點證據通過。**
- 富果 Developer 真正歷史日K及5m先前已由 PR #321、Run #42416763557 核對；0050固定研究策略跨來源重跑 Run #42416924677 與 FinMind 一致，但不代表事件策略正期望。

## 逐筆紀錄（重要語意）
- provisional key 為來源、代碼、營收月份，或來源、代碼、重大訊息主旨／發言日期時間的穩定 hash。**不是交易所提供的唯一事件 ID**；主旨修改、合併公告及重新公告可能造成 provisional identity 改變，待來源級正式識別驗證。
- 內容指紋變動：記錄為同 provisional key 的新觀測版本；不能當作新獨立交易樣本。
- 首次觀測：直接取 SHA256 manifest 的 `observed_at_utc`，不能由營收月份、出表日期、重大訊息「發言時間」推估原始公告時間。
- 原始發布時點 `issuer_original_published_at=None`，來源真實性未驗證；`eligible_trade_events=0`。
- 資格 Gate 不接受只新增「有公告時間」欄位，還需驗證來源、獨立查核回執與時間順序。仍不允許從預備證據產生正式交易或正期望。
- 存在與前期暫定 key 內容相同的紀錄才算 unchanged；變更會保留修正版本。跨日合併需讀取先前可信 ledger；目前未有 GCS 長期保存或逐日合併工作流，因此 PR 的單次實跑只建立初始帳本。

## 實測紀錄
- 首次研究實跑 Run #42418788042：四個官方資料來源成功（TWSE 月營收 1088、TPEx 月營收 893、TWSE 重大訊息 5、TPEx 重大訊息 285），共 `2271` 個暫定事件紀錄；新增 2271、重覆 0、變更 0、PIT 可交易事件 0。6 項事件帳本測試通過。
- 加入 Revenue → Fugle 回溯資格審核後再跑 Run #42418951929（結果須以 Actions 日誌確認）。不能僅靠既有富果價格可讀就產生營收事件回測。
- GitHub Artifact 僅短期保存，不代表 GCS 長期可用。

## 真實 GCS E2E 阻礙
目前連結的 GitHub 工具只能管理程式、讀取 workflow，沒有可存取 GCS bucket、GCP IAM/WIF、GitHub repo Secret/Var 的管理動作，也沒有通過授權審核的 GCS 身分執行。
- 必須驗證雲端 Bucket 名稱、區域、保留期限、object version/retention、WIF 主體、只限 repo 及 workflow 的信任設定、服務帳戶最小權限與帳單。
- 請不要在聊天提供金鑰。必要時需持有者在 Google Cloud Console 與 GitHub Repo Settings 授權設定後，於審查合併後的 workflow 手動 `workflow_dispatch` 真實讀寫，查完五個物件完整回讀與雜湊、可讀報告、失敗處理，才可宣告 Cloud persistence PASS。
- 不在未確認真實權限的情況下啟用 GitHub 定時排程，不改 Production。

## 正式事件策略回測解鎖條件
1. 建立來源等級不可改的正式文件與公司原始公告時間，而不是僅 first_observed_at；歷史回補不能把 2026 研究資料當全新 OOS。
2. 對 0050、1101 等已驗收富果行情的資料模型，仍須將**合格事件**依已凍結 Revenue MoM 5D 規則轉成訊號，次交易日實際可成交區間，0.45%/0.65%成本壓力、1R/單檔/組合風控入帳。
3. 核對 Walk-forward、不同市況、前瞻樣本門檻及 W0/P0-G 正式治理；如合格事件數為0，回測應明確顯示 `INSUFFICIENT_DATA`，而非偽造回測或調參。

**此文件是工程和研究驗收證據，不是交易建議。**
