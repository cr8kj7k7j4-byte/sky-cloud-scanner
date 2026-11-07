# 個股融資維持率來源驗證（2026-11-08）

狀態：INSUFFICIENT_DATA / RESEARCH_ONLY。不得作為交易訊號。本報告不修改 Production、不新增排程、不暴露 API 金鑰。

## 查證結果
1. Fugle Developer 公開 REST 端點類別涵蓋 intraday、snapshot、historical、technical、corporate-actions、ownership，沒有列出個股融資維持率。這不能證明所有非公開產品都不支援。https://developer.fugle.tw/docs/data/http-api/getting-started/
2. 已連接的 ChatGPT Fugle-Stock 服務 list_content_specs：FCNT000003「近半年融資融券」accessible=true，未列「融資維持率」類型。以 2330 呼叫 FCNT000003，沒有取得可核對的有效數值。ChatGPT 連接器權限不代表 Fugle Developer Key 的付費權限。
3. FinMind TaiwanStockMarginMaintenance 為 Sponsor 會員限定的個股每日推估值，包含融資維持率、融資成本線、融資餘額、融資成數；非券商實際整戶維持率。https://finmind.github.io/tutor/TaiwanMarket/Chip/
4. TWSE/TPEx 公告融資融券餘額，但沒有足夠的公開個股融資加權成本來唯一重建真實維持率。https://twse-regulation.twse.com.tw/TW/law/DOC01.aspx?FLCODE=fl007121&FLNO=69

## 資料契約
- 必備欄位：source、symbol、asof_date、retrieved_at_tpe、metric_name、value、unit、is_estimated、coverage、entitlement_verified、raw_evidence_id、missing_reason。
- 必須明確分離 estimated_market_symbol（個股市場估算）及 actual_account_collateral（證券商帳戶真實維持率）。缺融資成本、融資成數或合法權限時回傳 null，不得補造。
- FinMind 公開估算方式為 close / (margin_cost * margin_ratio) * 100。margin_cost 是模型估算移動加權成本，不能以當日股價或融資餘額代替。
- 個股估算值低於 130% 不代表特定帳戶確實面臨追繳或斷頭。

## 尚待實際驗收
- [x] 建立安全唯讀驗收程式 research/data_sources/fugle_entitlement_smoke.py 與單元測試 tests/test_fugle_entitlement_smoke.py（上市 2330 / 上櫃 6488；僅測文件已列 GET 端點，不輸出密鑰/回應本文）。
- [ ] 真正以已保管的 GitHub Actions 金鑰執行 HTTP 測試、取得真實執行日誌及測試產物：**尚未執行**，目前 GitHub 連接器沒有提供 Secrets 閱讀及 workflow_dispatch 操作，因此不得報稱驗收通過。
- [ ] 向 Fugle 確認付費開發者方案是否另有未公開個股維持率服務。
- [ ] TWSE/TPEx 融資融券餘額擷取，需上市與上櫃逐日驗證，僅可標記為融資餘額。
- [ ] FinMind Sponsor 有合法既有權限才做實際 API 測試；不建議新增付費。
- [ ] 若研究新風險特徵，依 PIT/OOS/Walk-forward/成本後與 W0/P0-G 治理要求獨立驗證，不能直接升 Production。

## 結論
富果 Developer 的個股融資維持率尚未證實可取得。暫時維持率設為缺值，官方融資餘額可作研究候選；正式 Sky 模型保持不變。
## 2026-11-08 工程更新
- 建立隔離的研究分支與草稿 PR #304。新增安全 smoke probe 及 mock 單元測試原始碼，但**尚無單元測試實跑結果**；單元測試存在不代表已通過。
- 使用者既有金鑰不應貼到 ChatGPT 或 GitHub 程式碼中。實際執行需授權環境中的環境變數 FUGLE_API_KEY，安全來源待核查。
- 即使 smoke PASS，僅表示 2330/6488 文件所列基本資料端點可讀；**不能證明市場融資維持率、全市場覆蓋、付費行情全功能、延遲或正期望策略已驗證**。
