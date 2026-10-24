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

python -m research.ml_validation_gate \
  --walk-forward research_output/walk_forward.json \
  --cost-stress research_output/cost_stress.json \
  --out research_output/ml_validation_gate.json
```

Promotion Gate：
- Walk-forward：必須通過
- Independent OOS：必須通過
- 成本壓力測試：必須通過
- Leakage 檢查：必須通過
- Paper Trading：必須通過

在五項全部通過前，P0-ML 一律維持 **RESEARCH_ONLY**，不得升級成 Production 或繞過 P0-R 風控層。
