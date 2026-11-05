# W0 / P0-OPS Scanner Fastpath acceptance (2026-11-06)

Status: CI-VALIDATION; LIVE-SESSION BEFORE/AFTER BENCHMARK PENDING; NO PRODUCTION MERGE AUTHORIZED BY THIS DOCUMENT.

Patch: PR #272 changes only .github/workflows/scan.yml; removes redundant successful-run preflight requests from critical path, preserves failure-triggered diagnostics, wraps original src.main with monotonic duration evidence.

## Static safety checks
- Keep the five Asia/Taipei official slots 09:05/09:15/09:30/09:50/10:15.
- Keep trading-calendar gate, strict official quote coverage gate, risk environment, source health failure alert and existing artifact upload.
- Failures propagate from original scanner; telemetry records exit code and duration.
- The fastpath is not a solution to absent TPEx official full-market realtime entitlements, missing actual executed last trade, or incomplete production trade provenance.
- Production strategy logic is unchanged in this patch.

## Remaining release gates (must not be skipped)
1. Verify all PR checks plus specialized fastpath regression.
2. Collect representative 09:05–10:15 main-baseline time and quote coverage traces; benchmark PR changes under comparable market conditions, including failure-diagnostic behavior and upload.
3. Check data coverage and portfolio/risk/safety state unchanged; do not improve speed by relaxing data coverage gates.
4. W0/P0-G signoff, then merge under deployment governance and observe actual weekday schedule run from main.
5. Read actual run log/artifact and confirm five intended schedules, including no duplicate run and no missing alert.

Main remains authoritative until signed release; a green CI is only evidence that regression checks passed, not a production speedup.
