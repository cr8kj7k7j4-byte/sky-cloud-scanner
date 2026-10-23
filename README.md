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
