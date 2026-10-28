# Chat-triggered Sky Swing 5D whole-market scan request

This directory is an operational request queue, **not** an investment signal or strategy change.

## Trigger contract

To execute the user command `Sky Swing 5D 快掃` from a GitHub-connected assistant, create a **new uniquely named file** at:

`scan_requests/swing5d/YYYYMMDDTHHMMSS-unique.json`

on `main` using GitHub's create_file operation.

Minimal file contents:

```json
{"command":"Sky Swing 5D 快掃","requested_at_taipei":"2026-10-28T09:00:00+08:00","purpose":"read-only whole-market research candidate scan"}
```

The `Sky Swing Live Whole-Market Scan` GitHub Action listens to pushes limited to this path. It runs the already existing `src.swing_live_scanner --mode swing5d` with the original risk filters. This creates **no orders** and **does not promote** the HOLD research model.

## Reading results

1. Find the newest matching workflow run after the trigger commit; use its run ID (not an earlier successful run).
2. Require successful completion and find its `sky-swing-live-<run-id>` artifact.
3. Read `latest_swing5d.json` or `latest_swing5d.txt`; verify `generated_at`, quote coverage, universe size, and `operational_full_market_scan`.
4. Show all candidate rows as **觀察** unless a separately validated Production rule creates an executable signal. Missing buy, stop or RR must remain —, not guessed.
5. If action is queued, failed, unavailable, stale or artifact cannot be read, clearly state **尚未取得本次即時掃描結果**; do not recycle yesterday's output as today's.
6. If `operational_full_market_scan` is false or sources are unavailable, fail closed for an alleged full-market result.

## Boundaries

- Coverage across TWSE + TPEx is operational and TPEx intraday uses the documented MIS OTC fallback; never claim TPEx-official certification.
- 5D is `RESEARCH_ONLY_HOLD`; ranking is **not** A+ nor a validated positive-expectancy strategy.
- Requests are Git commits and remain in repository history; store **no secrets, account balances or personal identifiers**.
- Avoid duplicate requests for the same user turn and do not create request files on feature branches (workflow listens to `main`).
- GitHub Action permission must allow pushes to `main` for the assistant; otherwise this command remains a read-only status query.
