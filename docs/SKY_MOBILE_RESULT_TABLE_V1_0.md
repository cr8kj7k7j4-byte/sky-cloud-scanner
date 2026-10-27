# Sky Mobile Result Table Contract v1.0

Status: Production presentation contract  
Date: 2026-10-27

## Canonical table

All current-state Sky scan/update outputs should prioritize this table when there is one or more stock candidate:

| 股票 | 現價 | 方向 | 多方評分 | 空方評分 | 買進觸發 | 最高接受價 | 停損／失效 | 分類 | 現在動作 |
|---|---:|---|---:|---:|---|---:|---|---|---|

Applies to:
- Sky 快掃
- Sky 當沖現在掃一次
- Sky Swing 5D 快掃
- Sky 波段現在掃一次
- Sky 波段快掃
- Sky Swing V1.1｜現在掃一次
- single-stock update / full analysis where the same fields are meaningful
- position/alert output may reuse the table, while position-specific P&L fields remain separate

## Field rules

- 現價: newest obtainable quoted price; include a data timestamp outside the table.
- 方向: evidence direction, not a prediction guarantee.
- 多方評分 / 空方評分: 0–100 evidence-comparison scores; never call them probability or win rate.
- 買進觸發: must be conditional. If no governed trigger exists, use "無有效多方觸發" or a clear non-executable description.
- 最高接受價: must be "—" when no governed max-entry rule exists. Never invent one to complete the table.
- 停損／失效: governed stop/invalidation only. If unavailable, "—".
- 分類: A+ / A / X only.
- 現在動作: only 買進 / 等待 / 觀察 / 續抱 / 加碼 / 減碼 / 停損 / 退出 / 禁止交易.

## Score governance

Display evidence scores are presentation-only and:
- are NOT statistical probabilities;
- are NOT historical win rates;
- do NOT feed P0-O ranking;
- do NOT feed P0-C decisions;
- do NOT feed P0-R sizing/risk;
- do NOT change Alpha, Trigger, Stop, Target or Promotion state.

If observable inputs are insufficient, show "—" rather than fabricate a score.

## V1.1 special rule

Sky Swing V1.1 keeps its frozen D-close signal / D+1-open entry semantics.
If the D+1 opening entry window has already passed:
- 買進觸發: show the original D+1 open and "(已過，不追)";
- 現在動作: 禁止交易;
- current intraday price must never be rewritten into a new trigger.


## Quick-scan emphasis v1.1

所有快掃／掃一次輸出固定採 10 欄表格。股票、現價、分類、現在動作以粗體呈現；多空評分差距達 10 分以上時，較強一側以粗體呈現；沒有治理後價位時顯示 —，不得補假數字。


## Update-command presentation v1.2

所有包含「更新」的 Sky 指令，一律先輸出同一張 10 欄主決策表：

| 股票 | 現價 | 方向 | 多方評分 | 空方評分 | 買進觸發 | 最高接受價 | 停損／失效 | 分類 | 現在動作 |
|---|---:|---|---:|---:|---|---:|---|---|---|

適用包含但不限於：
- Sky 快掃更新
- Sky 當沖更新 <symbol>
- Sky 波段更新 <symbol>
- Sky Swing 5D 更新 <symbol>
- Sky 當沖持倉更新 <symbol> ...
- Sky 波段持倉更新 <symbol> ...
- Sky 持倉更新 <symbol> ...

格式規則與快掃完全相同：
- 股票、現價、分類、現在動作固定粗體。
- 多空評分差至少 10 分時，較強一側粗體。
- 最高接受價有治理後有效值時粗體。
- 無有效價位顯示 —，不得補假數字。
- 持倉更新可在主表之後追加成本、張數、毛損益、淨損益等持倉資訊，但不得改變主表欄位。


## Unified presentation v1.3

自 2026-10-27 起，所有 Sky 即時決策主表（快掃、掃一次、更新、單檔分析、持倉更新、警戒等適用 10 欄主表者）統一採以下顯示規格：

| 股票 | 現價 | 方向 | 多方評分 | 空方評分 | 買進觸發 | 最高接受價 | 停損／失效 | 分類 | 現在動作 |
|---|---:|---|---:|---:|---|---:|---|---|---|

固定格式：
- 股票：粗體。
- 現價：粗體。
- 方向：一般文字，可顯示偏多、偏空、震盪、弱勢反彈、強勢過熱等可觀察結構描述。
- 多方評分：固定為 **XX / 100**。
- 空方評分：固定為 **XX / 100**。
- 買進觸發：整欄粗體；必須是條件式文字，無合法觸發則顯示 **無有效多方觸發** 或治理允許的等價文字。
- 最高接受價：有合法價位時粗體；沒有則顯示 —。
- 停損／失效：整欄粗體；只能使用治理後停損／失效條件。
- 分類：粗體，僅 A+ / A / X。
- 現在動作：粗體，僅使用既定中文動作集合。
- 缺少治理後資料時顯示 —；不得為了完整表格補造價位或分數。


## Unified display v1.3

All Sky current-state tables use the same 10 columns. Bull and bear scores render as bold `XX / 100`. Current price, trigger text, valid max-entry, invalidation text, classification, and current action render bold when present. Missing governed values remain `—`. This is presentation-only and does not alter strategy logic or risk controls.
