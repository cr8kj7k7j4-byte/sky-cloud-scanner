# Isolated governed repair permission retest

Purpose: trigger a new `pull_request synchronize` event on the existing Draft PR #527 after repository Actions PR-creation permission was enabled by the owner on 2026-11-11 (Asia/Taipei).

- Keep the deliberately broken single smoke fixture unchanged for the canonical repair controller to diagnose.
- Only offline `Sky Chat Bridge Unit Checks`; no Fugle API, no Production modification, no order, no automatic merge.
- Acceptance requires source failed CI → canonical governed-repair run → Actions-created Draft PR → dispatched downstream CI → read-back Artifact, with source and repaired SHA recorded.
- This file is a retry audit marker, **not** simulated trading or market-data evidence.
