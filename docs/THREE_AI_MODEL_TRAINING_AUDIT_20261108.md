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

## Research-observation prototype (additional work in PR #324)
- `research/three_model_research_signals.py` creates three **separate horizon-specific, deterministic technical observations** from supplied 5m / daily OHLCV JSON. It does not fetch Fugle, and it must NOT be described as a trained AI predictor. `source: FUGLE` is merely an input claim; `provider_response_verified=false` is always published until API integration is independently proven.
- The two daily-mode observation rules are technical placeholders, NOT horizon-tailored trained strategies. Short borrowability, tick rounding, full spread/slippage and current source latency are not validated; all price levels are hypothetical reference levels.
- Every observation carries `model_id`, deterministic `signal_id`, observed bar time and reason; hard-coded `production_signal=false`, `order_authorized=false`, `eligible_strategy_trade=false`, `realized_net_pnl=null`. Missing, duplicate, future-dated or invalid OHLCV rejects the relevant model safely.
- Input JSON top-level keys: `as_of` (timezone-aware ISO8601), `source` (`FUGLE`), `symbols` (symbol -> `name`, `bars_5m`, `bars_daily`); bars require timezone-aware `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- Run: `python -m research.three_model_research_signals --input research_data/verified_history_input.json --out research_output/three_models/research_observations.json`. **Do not create, fill, or present synthetic history input as real Fugle evidence.**
- Offline tests: `python -m pytest -q tests/test_three_model_evidence_gate.py tests/test_three_model_research_signals.py`; CI runs on PR changes, not on a paid API schedule.
- Current deployment blocker: no authenticated paid Fugle historical ingestion/readback, no persisted observation backend with de-duplication across runs, no Cloud Run source/revision, endpoint wiring or mobile end-to-end acceptance. The GitHub PR is **not** deployed, merged or training-complete.

## 2026-11-08 addendum: actual Fugle source adapter and private observation ledger
- `research/three_model_fugle_pipeline.py`: calls authenticated Fugle REST `/historical/candles/{symbol}` with separate 5-minute and daily timeframes; validates returned symbol, timeframe, date range, OHLCV and timezone, then calls the three-horizon **research-only** observer.
- Historical data cannot be treated as live intraday execution. The workflow rejects an unfinished current trading day prior to 16:30 Asia/Taipei. It does **not** prove exact execution price or permissions for margin shorts.
- `upload_immutable`: writes one JSON blob per valid observation to a **private** GCS bucket with generation-match=0, idempotent replay and fail-closed collision conflict. Stable observation identity is based on model + symbol + bar timestamp + source + direction, not transient run time; run `as_of` lives in the separate audit summary.
- `.github/workflows/three-model-fugle-private-ledger.yml`: **manual-only**, no cron, no auto orders, no deployment. Requires GitHub secret `FUGLE_API_KEY`, GitHub secrets `GCP_WIF_PROVIDER` and `GCP_SERVICE_ACCOUNT`, GitHub variable `SKY_RESEARCH_GCS_BUCKET`; the private bucket must allow object create/read for the workflow identity. CI runs fixture tests without reading secrets. Private prices must not be uploaded as public Actions artifacts.
- Workflow is available for manual default-branch dispatch **only after governance-approved merge**; its existence on a draft PR is not a successful paid API fetch or GCS write.
- `research/three_model_mobile_projection.py`: sanitized **schema adapter**, no authenticated web route; explicitly keeps training unverified, execution prohibited and Cloud Run deployment false. Existing live Cloud Run app code/service revision is not identified here, so no real web deployment, browser check, mobile screenshot, or live signal claim is possible from this PR alone.

### Acceptance order
1. GitHub offline contract CI passes.
2. Confirm IAM and a private storage bucket, inspect actual paid historical run output with 4 data requests for a two-symbol sample; validate `saved_records`, object existence/readback and duplicate rerun.
3. Obtain the source repository, GCP project, Cloud Run service and current running revision for `tw-ai-mobile-816937852055.asia-east1.run.app` using authorized tooling. Build integration on a review branch; deploy a non-trading authenticated read-only API path first.
4. Verify endpoint status, Chinese table fields, data/bar timestamps, absent price case, fault mode, unauthorized access, and mobile viewport before production traffic cutover.
5. Backtesting/training and W0/P0-G go/no-go are separate. There is currently **no evidence of successful GCP deploy or three AI model training**.

## 2026-11-08 live GitHub Actions authorization diagnosis
A research-branch push triggered `.github/workflows/three-model-cloud-auth-preflight.yml`, which checked **presence only** of required GitHub Secrets/Variables without printing their values. The resulting sanitized PR comment confirms:
- `FUGLE_API_KEY`: present in Actions secret environment (this does not prove paid historical endpoint access).
- Missing: `GCP_WIF_PROVIDER` Secret, `GCP_SERVICE_ACCOUNT` Secret, `SKY_RESEARCH_GCS_BUCKET` Actions Variable.
- Google Workload Identity Federation authentication and GCS read were skipped. No paid API call, no GCS write, no Cloud Run deploy.
- Evidence: PR #324 discussion comments, latest at https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/324#issuecomment-6714157345
- Therefore the next necessary external setup is to create/identify the correct private GCS bucket and GitHub OIDC/WIF service account authorization in the actual GCP project, then set the three names above in GitHub. **Never paste secret values into chat, PR comments or public code.**

The research GCS ledger now stores rejected/no-trade decisions as immutable records with stable `rejected-...` IDs, not just accepted observations. All records are explicitly marked `production_signal=false`, `order_authorized=false`, `eligible_strategy_trade=false`, and never imply real P&L.
