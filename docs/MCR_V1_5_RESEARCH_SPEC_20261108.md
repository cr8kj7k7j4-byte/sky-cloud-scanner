# Sky MCR V1.5｜融資清洗事件與成交品質決策模型（研究候選）
建立日期：2026-11-08。狀態：INSUFFICIENT_DATA / RESEARCH_ONLY。**不是 Production，不提供真實買賣指令。**

## 核心問題
比較 A 一般超跌、B 超跌加融資壓力、C 加融資清洗、D 加賣壓衰竭／買盤與價格確認、E 加實際成交與完整風控，是否產生樣本外可重複的「成本後」增量優勢。若融資指標缺乏額外資訊，停止擴建。

## 交易假設／階段（不代表已驗證門檻）
- S0：市場環境、重大公司／產業事件、交易資格。
- S1：FinMind **估算**個股維持率（候選區分 <120、120–130、130–150、>=150）；**非券商實際整戶維持率，低於130不等於斷頭**。
- S2：融資餘額日／3日／5日變動、融資成本線距離、首次跌破／回升130的事件時鐘。
- S3：價格未再創低、同等賣出流量的價格衝擊減少（需逐筆資料證據，不可由K線推定為強迫賣出）。
- S4：已成交主動買量比率，買方持續性、委託流失衡；五檔掛單不能充當已成交買盤。
- S5：突破／二次回測／VWAP價格確認，以互斥研究組比較，不事後挑最佳。
- S6：價差、流動性、成本壓力、停損、RR、部位與 Kill Switch。
- S7：模型失效、價格過度延伸、訊號逾期，維持觀察或禁止交易。

## 現有研究引擎
`research/mcr_v15.py` 使用離線 JSON 輸入，評估 `financing` 與 `tape` 及 `portfolio`。
欄位：`published_at`, `observed_at` 必須為含時區 ISO8601；融資交易日必須早於判斷日；不接受未公布的當日融資資料。
輸出：`features`, `missing`, `failed`, `classification` 和 `production_signal=false`。所有價格與研究張數僅供模擬，**不得自動下單**。
安全：缺少真實持倉、停損、資料時間或主動成交證據時不可成為可交易訊號；做空獨立研究，需要證券借貸、資格及成本驗證。
研究門檻觀測：買量比率 >55%只是候選特徵，不是驗證過的最佳進場界線。

```bash
python -m unittest tests.test_mcr_v15 -v
python -m research.mcr_v15 --input research/mcr_sample_input.json --output /tmp/mcr_result.json
```

## 未完成的真實資料鏈
1. FinMind `TaiwanStockMarginMaintenance` 與 `TaiwanStockMarginPurchaseShortSale`：確認帳號權限、逐筆 API 回傳、資料日期與發佈時間；不可推論 Sponsor 已驗收。
2. Fugle 授權範圍內之 trades/books/candles：確認可否穩定雲端取得、是否保留委託取消或主動買賣分類；無證據不得用內外盤冒充委託流。
3. 盤後 FinMind -> 隔日盤中 Fugle 的 point-in-time (PIT) 時序、全市場上市櫃股票歷史母池、下市股票與除權息處理。
4. 尚未建立全市場事件回測、嚴格樣本外、滑價與成交品質驗證；`production_signal` 固定 false。
5. 手機通知、時間表與 GitHub Actions 日誌未驗收前不得宣稱已開啟即時警戒。

## 必須通過的研究治理
來源：`SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`。
事先登錄 universe、horizon、樣本切分、候選門檻、進出場、重大事件排除、成本、比較基準、容量與 Kill Switch。
禁止將既有 ARCHIVED_NO_RETUNE 突破／回測策略重新命名並局部調參。2026年已使用資料不得稱為 fresh OOS。
測試：0.45%主要／0.65%壓力成本、至少3個 walk-forward folds、牛／盤／熊、風險報酬、獲利因子、最大回撤、集中度、樣本獨立性。
前瞻：>=200筆可評估樣本、>=20個真正未來交易日、>=2類市場環境、>=95%完成率、單檔占比<=20%。W0/P0-G審查之前不得改 Production。

## 風控
總資金500,000元；每筆風險上限5,000元；單檔100,000元；最多3檔；組合未平倉風險15,000元；當日淨損達10,000元或連續2筆停損停止新進場。
研究數量不是可下單張數；要另檢查實際持倉、盤中成交與交易單位。固定已校準費率不是完整成交成本。

## 當前結論
INSUFFICIENT_DATA。尚未得到可交易正期望、即時行情完整率或正式買點。程式碼完成不等於研究通過。
