# FinMind API 驗收 — 2026-11-08

## 目的與範圍
- 僅驗證已設定在 GitHub Actions Secrets 的 `FINMIND_TOKEN` 是否可以讀取歷史資料。
- 測試對象：2330，2026-10-26 至 2026-10-30（固定過去交易週，避免非交易日空資料）。
- 測試資料集：`TaiwanStockPrice`、`TaiwanStockMarginPurchaseShortSale`、`TaiwanStockInstitutionalInvestorsBuySell`、`TaiwanStockMarginMaintenance`（Sponsor 專用）。
- 驗證 HTTP 連線、非空資料、基本欄位、回傳日期。每個資料集最多一次請求。
- 回傳 JSON 不包含 token、原始資料列或 HTTP 請求 header。
- API 參考：https://finmind.github.io/login/ 及 https://api.finmindtrade.com/docs

## 執行
此功能是獨立驗收，不修改 Production 掃描、交易訊號或排程。
- 測試分支 `integration/finmind-api-acceptance-20261108` 上推送本驗收檔案會觸發一次 Actions；`main` 不具有相同 push 觸發。
- 合併至 main 後可在 Actions 手動執行 `FinMind API entitlement acceptance`。
- 查看該次 Run 的 `finmind-entitlement-acceptance` artifact，檔案 `finmind_acceptance.json`。
- PASS 僅代表指定欄位及指定日期讀取成功；無法據此認定全市場歷史涵蓋率、點時性（PIT）、即時行情、融資維持率的真實帳戶數值或策略有正期望值。個股融資維持率即使 PASS 也是 FinMind 盤後估算，不是券商實際整戶維持率。
- 如 401、403、429、空資料或缺欄位，保持 FAIL 並記錄原因，不自動降級為無驗證的行情來源。
- 研究治理仍依 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`。
- 秘密值更新時應在 FinMind 官方撤銷已外露的 Token；程式僅從 Actions Secrets 讀取。

## Sponsor 個股融資維持率驗收擴充（2026-11-08）
- 同一條 GitHub Actions 分支 push 觸發，不新增週期排程。第四項只讀查詢 2330，固定 2026-10-26 至 10-30，資料集 `TaiwanStockMarginMaintenance`。
- 必查欄位：date、stock_id、margin_balance、margin_cost、margin_ratio、margin_maintenance；維持率及成本線須為正數，融資成數須在 (0,1]，查詢標的必須為 2330。
- 只輸出 HTTP 狀態、資料列數、日期、缺少的欄位與分類錯誤。不得輸出 token 或整批原始資料。
- 失敗（401/403、200 空資料、schema 異常）即標記 FAIL；若只有前三項 PASS，維持率仍不得宣稱有權限。
- 真正 HTTP 讀取結果以 `finmind-entitlement-acceptance` Artifact 為準；CI 綠勾可能只是其他測試，不能替代此項驗收。
- 官方欄位與估算限制：https://finmind.github.io/tutor/TaiwanMarket/Chip/

## GitHub 實跑證據（2026-11-08 04:13 台灣時間）
- [Workflow Run #42410017271](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42410017271) / job id `128515908258`，結果 **failure（正確 fail-closed）**。
- 離線 `unittest`：6/6 PASS。
- `FINMIND_TOKEN` 已設定（不記錄其內容）。
- `TaiwanStockPrice` HTTP 200 PASS；`TaiwanStockMarginPurchaseShortSale` HTTP 200 PASS；`TaiwanStockInstitutionalInvestorsBuySell` HTTP 200 PASS。
- **`TaiwanStockMarginMaintenance` HTTP 400 FAIL**（已確定請求被 API 拒絕）。HTTP 400 本身不能證明是哪個權限規則、也不應冒稱已收到官方 Sponsor 否決解釋。
- Artifact：`finmind-entitlement-acceptance`，ID `13589620268`（完整的安全摘要）。上傳成功。
- 這項結果已證明一般資料可用，但 Sponsor 個股融資維持率尚不可使用。無需重複測試基本三項，也不應持續 400 重試耗用配額。
- 正式策略不變，狀態：`RESEARCH_ONLY / INSUFFICIENT_DATA`。後續僅在有官方授權變更、端點修正證據時重驗。
