# 全球融資賣壓與反轉研究：證據及資料缺口
2026-11-01 | W7 research intake | HOLD / NOT PREREGISTERED

## 核心問題
已公開的台股融資餘額變化，在同樣跌深與價格轉強條件下，是否能提供額外、穩定、可執行的成本後預測資訊？融資餘額變化不能確認追繳、斷頭、個人維持率或賣壓衰竭。

## 一手來源與可轉移限制
1. Bian et al. (2018), NBER WP 25040 https://www.nber.org/papers/w25040 ：中國 2015 年、帳戶層級槓桿與股票曝險資料。接近槓桿上限帳戶的持股賣壓上升，股票先異常下跌後部分反轉。NBER 摘要指出差異 10–15 交易日較大，30–40 日減弱。台股公開個股融資餘額不能複製該文帳戶層級辨識，也不證明 3–5 日有效。https://www.nber.org/digest/nov18/leverage-fire-sales-and-2015-chinese-stock-market-crash
2. Coval & Stafford (2005/2007), NBER WP 11357 https://www.nber.org/papers/w11357 ：美國基金申購贖回造成持股賣壓，流動性供給者後續報酬顯著；樣本及資金機制不同於台股個人融資。作者全文對照非受限基金賣出無明顯反轉，顯示需要對照組。https://www.hbs.edu/ris/download.aspx?name=Asset+Fire+Sales+in+Equity+Markets.pdf
3. Huang, Ringgenberg & Zhang (2023), Management Science https://doi.org/10.1287/mnsc.2022.4585 ：基金火售可能帶有負面資訊，價格可長期偏弱，不能把每次融資下降都視為非資訊賣壓或必然反彈。
4. 呂振揚（2016），中央大學碩士論文 https://ir.lib.ncu.edu.tw/handle/987654321/71763 ：台灣融資水準與後續報酬之橫斷面關係，摘要描述約六個月的反轉關係；不等於融資急減之因果證明或短線可交易效益。
5. TWSE 法規：整戶低於130%屬追繳條件，處分具時間及例外；不等同個股130%買點。https://twse-regulation.twse.com.tw/TW/law/DOC01.aspx?FLCODE=fl007121&FLNO=54 https://twse-regulation.twse.com.tw/TW/law/DOC01_print.aspx?FLCODE=FL007121&FLNO=55

## 系統現況（截至本文件日期）
PR #193 在 main 建立 research/margin_evidence/collect.py 與 .github/workflows/margin-evidence.yml。PR 雲端 run 41264175599 通過基本測試及 2026-10-30 兩市場報表抓取；這不是正式排程成功、資料完整性、歷史PIT或策略績效的證明。工作流程 cron 11:30 UTC 週一至五（台灣19:30），依現有交易日曆決定是否抓取，產物保留90天；不構成持續長期資料庫，必須先解決到期、缺漏、修訂保留及重新擷取追蹤。僅單日、行數和日期基本檢查，100筆下限不代表全市場覆蓋率。上市上櫃行含非普通股，不能當合格股票母池。

## 下一步與停止條件
- W3A：確認兩市場報表欄位單位、資料實際可用時間、修訂與日曆、公告與來源變更；建立不可覆寫帶來源、擷取與版本的長期證據；以時點母池衡量缺漏、重複與覆蓋率，核對停牌、下市櫃與除權息。禁把日後下載的修正歷史當原始即時快照。
- 把經時點驗證的價格、成交量與融資報表使用可用時間連接；公告晚於收盤不可假設當日收盤可交易。必要時次交易日才入場；同一報表中的次日修訂不能提前使用。
- W0 判斷個股融資代理資料能否作為不同於封存 Weak-Regime Mean-Reversion 的結構性新資訊；未經裁定保持 intake，不局部調參復活。
- 預先固定單一主要 horizon 與對照策略、母池、事件/觸發、限價及停損、報價/停牌/跌停/缺口成交處理、排名、集中度、成本和資料切分；其他 10–40 天僅列候選研究問題，須重新獨立登錄，禁止挑結果好的 horizon。
- 與相同跌幅、價格與流動性條件但不看融資的 matched control 比較，採共同交易日及叢集穩健誤差，檢查獨立增益、regime、成本與組合風險。
- 使用 0.45% 與 0.65% 來回成本壓測，不混淆使用者已知費稅與完整滑價。2026 既用資料非 fresh OOS；至少三個 walk-forward folds，並完成前瞻門檻 200 筆、20 真正交易日、2 種環境、95% outcome、單一股票≤20%，才可送 W0/P0-G 審查。
- 實際處分成交資料如未取得，一律標註「融資變化代理」，不得宣稱斷頭或完成清算。無交易訊號、無升版、無自動下單。
