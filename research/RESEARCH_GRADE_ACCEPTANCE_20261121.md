# B01 Sky AI — Research-Grade Acceptance Gates (2026-11-21)

> Evidence ledger only. **Do not treat CI success as certification of live market-data semantics, trading strategy performance, or production deployment.**
> Scope: read-only research. No orders, no simulated ledger, no #508 dependency. Exclude the 31 Taiwan Innovation Board instruments.

## Verified baseline

- `main`: `8a9643919f15ce6bb5ab29552d7aad43e5d4b6e4` (PR #617 merged).
- PR #617 head CI: 19/19 successful; regression added for invalid/overflowing feature percentage ratios.
- Main push CI: [Sky Production E2E Acceptance run 44916880292](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44916880292) PASS; [W6 Forward Execution Evidence run 44916880275](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44916880275) PASS.
- Offline test coverage inspected: `tests/test_sky_v14_ticker_candles_probe.py` (26 test methods), `tests/test_sky_stage5_vwap_cost_evidence.py` (6), `tests/test_sky_paid_fugle_api_guard.py` (23), `tests/test_sky_fugle_request_identity.py` (8). **Coverage is not equivalent to a fresh standalone execution of each test file.**

## Gate ledger

| Gate | Acceptance evidence | Current status |
| --- | --- | --- |
| G0 code baseline | Main SHA, zero open PRs, green applicable CI | **PASS** as of review |
| G1 five-minute bars offline | timestamp grid, timezone, same-date, completeness, ordering, nonfinite OHLC/volume, unfinished bars fail closed | **COVERED BY TESTS**; CI passed; live source semantics not certified |
| G2 VWAP offline | provider avgPrice vs turnover/volume consistency; missing/invalid/overflow fail closed | **COVERED BY TESTS**; `vwap_certified=false` by design |
| G3 paid API cross-workflow dedup | same concurrency group, five-minute claim, uploaded ZIP nonce verification, duplicate and GitHub errors fail closed | **COVERED BY TESTS**; concurrent live execution proof pending |
| G4 latest-main mobile E2E | mobile request → same-run Fugle scan → artifact with matching run/request/SHA → independent readback | **PENDING** on main `8a964391` |
| G5 real-market five-minute bars | dated regular-session Fugle observations, start/end timestamp semantics, complete contiguous bars | **PENDING** next market session |
| G6 independent VWAP certification | explicit provider volume units, independently reconstructed price×volume, provenance and causality | **PENDING**; never substitute quote avgPrice alone |
| G7 final research-only sign-off | all mandatory evidence linked, no orders, no simulated ledger, TIB excluded, failure states documented | **PENDING**; do not claim live strategy launch |

## Controlled market-session procedure

1. Before spending: confirm the latest `main` SHA, no other paid scan running, Fugle credentials remain in GitHub Secrets, and reservation guard is enabled.
2. Run the existing [Sky Chat On-Demand Scan Bridge](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/workflows/sky-chat-bridge.yml) on `main` during a Taiwan trading session; never bypass its global paid concurrency or fail-closed claim.
3. Record run ID, SHA, request ID, artifact ID, trade date, snapshot counts, five-minute bar times, missing data and all rejection reasons. Reject weekend/after-hours output as proof of *live* five-minute-bar semantics.
4. Independently read back **the same run** artifact; reject SHA/request/run mismatch.
5. Record VWAP source units and an independent reconstruction; if units or causality cannot be proven, mark G6 **NOT CERTIFIED**, not PASS.
6. If the paid reservation is blocked, do not retry immediately; record `RECENT_RESERVATION` and inspect existing run evidence.
7. Final decision: research information service may be labeled **research-only** only for the functions independently evidenced. Do not label the complete live strategy accepted while G4–G7 are pending.

## Evidence hygiene

- Every PASS requires a stable GitHub run/commit/artifact link and expected result.
- `COVERED BY TESTS`, `PENDING`, `BLOCKED`, and `PASS` are distinct states.
- No autonomous order placement, no brokerage execution, no simulated trading ledger, no additional paid calls for offline validation.
