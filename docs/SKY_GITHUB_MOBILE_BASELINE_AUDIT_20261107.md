# Sky GitHub-first baseline audit — 2026-11-07

Decision source: docs/SKY_OPERATING_ARCHITECTURE_GITHUB_MOBILE_20261107.md (user confirmed).
This is a **read-only evidence snapshot**; no Production change or current-session live-quote certification.

## Code/config findings
- `.github/workflows/scan.yml`: scheduled cron UTC 01:05/15/30/50 and 02:15 on Monday-Friday, corresponding to Asia/Taipei 09:05/15/30/50 and 10:15. Contains `workflow_dispatch`, trading-calendar gate, source diagnostics, scanner, coverage verifier, report artifact upload and failure Telegram step.
- `src/diagnose_sources.py`: official universe + MIS diagnostic sample; Fugle individual quote and TSE/OTC snapshot probes, with plan_restricted and missing-executed-price distinctions.
- Production code does NOT use Nova in the documented main path. Nova PR #300 is draft and labeled HOLD.
- `docs/SKY_EXTERNAL_LATEST_STATUS.json` generated 2026-11-06T09:36:47Z; cannot represent real-time 2026-11-07 status.

## Observed workflow evidence (not necessarily latest run)
Run https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41763654250 (2026-11-04):
- `Run scanner`: success
- `Verify operational market coverage`: failure
- `Upload scan report`: success
- `Notify Telegram when intraday scan fails`: success as a GitHub step; end-user phone receipt NOT independently confirmed
- overall scan job conclusion: failure; fail-closed is correct.
- Issue #217 records 1,985-stock official pool, inadequate executed price coverage, MIS `z/pz` missing, Fugle bulk snapshot plan_restricted at GitHub runner. At the logged 10:54 run, report quote_coverage_pct=2.77, market_data_gate=BLOCKED_EXTERNAL_DATA_NO_TRADE.
- Swing evidence in Issue #217: 2026-11-04 run 41565093503 coverage 107/1985=5.39%; invalid as full-market executed-price evidence.
- Latest scheduled live-run coverage, all five-slot punctuality, mobile on-device access and notification delivery are NOT verified with currently accessible run listings/artifacts.

## Priority remediation / acceptance
1. Fetch most recent genuine *scheduled* runs of all five scan slots, compare event scheduled time vs runner start, log and artifact date; dedup / missed-slot detection, holiday handling.
2. Source check: TWSE, TPEx separately; forbid substituting prior close, bid/ask or OHLC for executed price; treat OTC MIS as fallback, verify permitted Fugle snapshot entitlement on runner.
3. Ensure report produced with reliable latest timestamp and human-readable Chinese mobile link even when market data is insufficient; no false READY signal.
4. Verify phone actual receipt plus failure path, retry and dedup; workflow notification step success does NOT prove delivery to intended phone.
5. P0-R and cost / W4 evidence are distinct from operational readiness; remain unchanged. No Nova cloud expansion, no new paid sources, no Production merge on thin evidence.

## Current verdict
`HOLD / BLOCKED_EXTERNAL_DATA_NO_TRADE` for *certified full-market intraday entries*, based on latest verified incident evidence. This is not proof the very latest schedule is still failing; it is proof that no verified recovery is yet established here.
