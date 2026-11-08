# Sky 三模型｜三項交付與驗收報告（2026-11-08 Asia/Taipei）

**狀態：研究基礎設施部分通過；全鏈路尚未通過；正式交易禁止。**

## 1. 富果真實歷史 API（PASS；僅限兩檔小樣本）

- 執行：GitHub Actions [42427083712](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42427083712)
- Workflow：`.github/workflows/three-model-fugle-api-smoke.yml`，觸發：研究分支 push。
- 程式：`research/three_model_fugle_api_smoke.py` 使用已配置的 GitHub `FUGLE_API_KEY`，呼叫真實 `historical/candles` 端點。
- 查詢截止 2026-11-06（已完成交易日），日K窗口約 20 日、5 分K窗口 1 日：
  - 1101：日K 13 筆、5 分K 54 筆，PASS
  - 8088：日K 13 筆、5 分K 53 筆，PASS
- 响應 symbol / timeframe / 時間範圍 / OHLCV 基本完整性已透過 adapter 檢查；分K成交量單位為「張」，日K為「股」，兩者不可直接加總比較。
- **未驗收：** 全市場覆蓋、即時報價、API rate limit/長期間重放、逐筆市場執行品質、企業行動調整、資料授權再散布。此次流程不公開 raw OHLCV，不接觸 GCS/Cloud Run/下單。

## 2. 決策帳本（OFFLINE PASS；GCS 真實研究決策落地 PENDING）

- `research/three_model_fugle_pipeline.py` 提供不可覆寫的逐筆私有 GCS JSON 物件（`if_generation_match=0`），重跑原紀錄須雜湊一致；相異內容須拒絕衝突。
- 正面訊號與 `NO_TRADE`／拒絕訊號皆必須入帳；不交易紀錄按研究日期建立穩定拒絕 ID，避免當成獨立交易重複計數。
- 保存 `production_signal=false`、`order_authorized=false`、`eligible_strategy_trade=false`、`realized_net_pnl=null`。
- 已測試：create-only、重跑冪等、碰撞衝突、安全狀態、拒絕紀錄、拒絕日期去重及專用 bucket 隔離。
- 已驗證獨立 GCP OIDC + GCS **診斷物件** 寫入 SHA256 讀回：[42426638982](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42426638982)。
- **未驗收：** 真實 Fugle 歷史行情生成研究決策並逐筆寫入研究 bucket 的工作流程，及相同輸入第二輪讀回冪等。其手動-only workflow 仍在 PR #324 Draft，未合併 main。

## 3. 手機戰情室資料契約（OFFLINE PASS；Cloud Run E2E PENDING）

- `research/three_model_mobile_projection.py` 產生中文且非即時、非交易、非 AI 權重的研究資料合約，明確標示模型、股票、行情時間、方向、拒絕原因、資格。
- 版本 v2 強制：完整呈現拒絕／`NO_TRADE` 研究紀錄；不捏造未取得的行情時間；拒絕重複 ledger ID；拒絕無時區 bar timestamp；回傳研究紀錄筆數、缺時間筆數、拒絕筆數等資料健康指標。
- 不提供虛構多空分數或無憑據可交易價位。
- **未驗收：** 原 Cloud Run `tw-ai-mobile` 實際程式碼、當前 revision、唯讀授權路由、網頁及手機 E2E。沒有完成部署，不能聲稱前端已上線。

## 4. 審查／風控結論

- 主分支正式策略及帳戶資金風控不變。PR #324 保持 Draft；2026 既有資料不視為新鮮 OOS。
- 三模型目前是 deterministic **研究觀察規則**，不是已受證據驗證的三個 AI 訓練模型，亦不是策略正期望值證明。
- 遵守 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`。
- **狀態：HOLD / RESEARCH_ONLY**。正式 Production 升級須 W0／P0-G 閘門、未來交易日和完整成本後結果，不可自動下單。

## 5. 下一個真正的阻礙

獨立的 OIDC/GCS 實測和富果唯讀實測皆成功。尚需經 W0/P0-G 工程與安全審查，決定是否合併 PR #324 的研究專用手動 ledger workflow；合併後才能在限制 `main + workflow_dispatch` 的 OIDC 下執行富果 → 研究決策 → 私有 GCS 寫入/重跑驗證。手機部署需另有 Cloud Run 管理授權及實際應用原始碼與版本，不得由 GitHub repo 路徑臆測已部署。
