# Sky v0.5 GitHub Research Workflow

這個 bundle **不修改正式 v0.4 scanner**。

上傳檔案：
- `.github/workflows/backtest-v05.yml`
- `research/download_intraday.py`
- `research/backtest_v05.py`
- `research/__init__.py`
- `tests/test_v05_pilot.py`

Pilot 預設：
- 2026-09-21 ～ 2026-10-22
- 18 檔近期候選/淘汰樣本
- 5 分 K
- 60 分鐘 forward horizon
- round-trip cost assumption = 0.45%

重要：
- Pilot 只驗證 Anti-Chase 的增量效果。
- 不是全市場回測，不驗證完整 Market Gate / Sector RS / Setup+Trigger / EES / RR。
- Pilot 通過後才進第二階段全市場 replay。


## P0-ML Training Pipeline

研究環境與正式 Cloud Scanner 分離；正式 runtime 仍使用 `requirements.txt`，ML 訓練使用 `requirements-ml.txt`。

流程：

```bash
pip install -r requirements-ml.txt

python -m research.build_ml_dataset \
  --data-dir research_data \
  --out research_output/ml_dataset.csv \
  --horizon-bars 12

python -m research.train_ml_models \
  --dataset research_output/ml_dataset.csv \
  --out research_output/models

python -m research.walk_forward_ml \
  --dataset research_output/ml_dataset.csv \
  --out research_output/walk_forward.json

python -m research.cost_stress_ml \
  --dataset research_output/ml_dataset.csv \
  --model research_output/models/xgboost.joblib \
  --out research_output/cost_stress.json

python -m research.shap_explain \
  --dataset research_output/ml_dataset.csv \
  --model research_output/models/xgboost.joblib \
  --out research_output/shap_summary.json

python -m research.audit_ml_dataset \
  --dataset research_output/ml_dataset.csv \
  --out research_output/leakage_audit.json

python -m research.ml_validation_gate \
  --walk-forward research_output/walk_forward.json \
  --cost-stress research_output/cost_stress.json \
  --leakage-audit research_output/leakage_audit.json \
  --out research_output/ml_validation_gate.json
```

Promotion Gate：
- Walk-forward：必須通過
- Independent OOS：必須通過
- 成本壓力測試：必須通過
- Leakage 檢查：必須通過
- Paper Trading：必須通過

在五項全部通過前，P0-ML 一律維持 **RESEARCH_ONLY**，不得升級成 Production 或繞過 P0-R 風控層。


## P0-K Knowledge & Evidence Engine

Sky 的研究輸入改採 Evidence-First：
- 多來源資料保留 source type / source name / URL / published_at / observed_at。
- Recency Gate：資料過期不得升級為主要交易依據。
- Conflict Resolver：同類證據互相衝突時，標記 REVIEW_REQUIRED。
- Hallucination Guard：無來源即時價格、成交量、財報、新聞與事件不得生成。
- Evidence Ledger 明確區分事實、推論與未知資訊。

## P0-A Agent Orchestration Layer

目前先導入：
- Market Agent
- Technical Agent
- Risk Agent
- Devil’s Advocate Agent

硬性護欄：
- 單一 Agent 不得直接交易。
- P0-R 風控不得被繞過。
- 缺少可追溯證據時不得升級交易信心。
- Agent 結果只提供給 P0-C 決策層使用。

此階段先以市場行情證據接入既有 scanner；新聞、財報、法說與產業資料後續再接至同一 Evidence Ledger。


## Sky Realtime Command Routing

Canonical contract: `docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md`

Realtime-first commands:
- `Sky 快掃`
- `Sky 當沖現在掃一次`
- `Sky Swing 5D 快掃`
- `Sky 波段現在掃一次`
- `Sky 波段快掃`
- `Sky Swing V1.1｜現在掃一次`
- single-stock `更新` / `完整分析`
- position `持倉更新` / `警戒`

Whole-market live scans use TWSE + TPEx official current universe with TWSE MIS TSE + OTC operational quotes, then Fugle single-stock realtime deep-dive where available. OTC via MIS remains an operational fallback and is not labelled TPEx-official realtime certification.

Backtest / validation commands remain historical Point-in-Time workflows and do not get rewritten into realtime scans.

Command parser: `src/sky_command_router.py`.
