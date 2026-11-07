# Three-model AI training gap audit (2026-11-08, Asia/Taipei)

Scope: **research-only**; no production trading changes, no orders, no Cloud Run claim.

## Verified main branch facts
- `research/build_ml_dataset.py` reads existing `*_5.json` 5-minute bars, builds one forward-return target using `horizon_bars=12`. It does not ingest Fugle directly.
- `research/train_ml_models.py` trains RandomForest and XGBoost regressors for that *one* target, writing joblib artifacts under an output directory. These are different algorithms, not the three independent strategies.
- `research/walk_forward_ml.py` has a research directional-accuracy walk-forward, insufficient for model promotion.
- `src/config.py` uses `FUGLE_API_KEY` for existing scanner configuration; this alone does not demonstrate paid historical download rights, training input continuity, or three-model inference.
- `SKY_SYSTEM_REGISTRY_V2_1.md` and `research/RESEARCH_FREEZE_REGISTRY.md` forbid relabelling archived failed strategies as production. Existing 2026 research is not untouched OOS.
- A direct Cloud Run URL check and full Git clone were unavailable in the current execution environment; front-end mapping and deployed revision remain unverified.

## Required implementation, in order
1. Obtain verified Fugle historical candles under paid quota; record symbol, exchange, bar period, market timezone, source timestamps, call authorization, failures, corporate actions and point-in-time universe. Never store API keys in files or logs.
2. Create three **separate** datasets, preregistered targets, train/validation/OOS time boundaries and embargo measured against each model's maximum label horizon:
   - `bidirectional_intraday`: minute-bars, long/short/flat; short eligibility and execution assumptions separately verified.
   - `next_day`: prior-known data only; entry at next executable price; overnight gaps and execution costs.
   - `swing_3_20d`: date/weekly context, overlapping 3–20 session labels, point-in-time corporate events.
3. Train distinct baselines and ML models; version all features, data fingerprints, code commit, model weights and reports.
4. Verify 0.45% primary / 0.65% stress costs per canonical protocol, actual calibrated execution profiles where applicable; validate leakage, regime, portfolio, drawdown and prospective evidence.
5. Generate `research_output/three_models/manifest.json` with the model fields and gate names in `research/three_model_evidence_gate.py`. Run:
   `python -m research.three_model_evidence_gate --manifest research_output/three_models/manifest.json`.
   The process deliberately exits 2 with missing/failed evidence. Even a complete report never authorizes production.
6. Only after file integrity/readback and governance review, integrate sanitized evidence summaries into mobile API. The UI must distinguish `UNTRAINED_OR_UNVERIFIED` from actual training and must not claim live pricing or profitability.

## Current completion
- Added a **fail-closed evidence integrity checker** and offline regression tests on a separate research branch.
- NOT completed: actual Fugle historical ingestion for all symbols, three independent model weight files, verified OOS/cost reports, runnable GitHub Actions training, Cloud Run deployment, mobile E2E testing, or W0/P0-G approval.
- Do not change the mobile badge from untrained based on this PR alone.
