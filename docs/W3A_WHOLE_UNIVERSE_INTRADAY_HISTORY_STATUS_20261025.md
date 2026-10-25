# W3A｜Whole-Universe PIT Intraday History Pipeline — 2026-10-25

## Current status
**ENGINEERING READY / DATA DOWNLOAD NOT YET EXECUTED**

This work addresses:
`EXTERNAL_DATA_REQUIRED:SYNCHRONIZED_WHOLE_UNIVERSE_INTRADAY_HISTORY`

## Completed engineering
1. Canonical PIT intervals already produced by:
   - `research/audit_historical_universe.py`
   - output: `pit_intervals.json`
2. New whole-universe downloader:
   - `research/download_pit_universe_intraday.py`
3. Downloader behavior:
   - selects every TWSE/TPEx symbol active at any time in the requested PIT window;
   - never derives the universe from today's listing list;
   - splits history into <1-year API chunks;
   - handles 404 as no-bars-for-period, not symbol failure;
   - handles 429 with bounded backoff;
   - supports deterministic 20-shard execution;
   - supports cached/resume behavior by chunk file;
   - outputs per-shard manifest + download summary;
   - computes successful-symbol coverage and 95% gate flag.
4. Manual whole-universe workflow:
   - `.github/workflows/w3a-whole-universe-intraday-history.yml`
   - 20 deterministic shards
   - `max-parallel: 1` to protect the Fugle rate limit
   - each shard uploads its own compressed artifact
5. Unit-test workflow:
   - `.github/workflows/test-w3a-pit-universe-download.yml`

## Why this replaces the 100-symbol diagnostic approach

The existing 100-symbol 5m artifact covers only about 4.8%–5.3% of the governed PIT universe at audited dates.
It remains valid for engineering diagnostics only.

The new pipeline consumes the union of PIT membership intervals, including symbols that later delisted, and therefore avoids using a current-only universe as the download manifest.

## Download gate

A whole-universe export is not accepted merely because the workflow completes.

Minimum first-stage source gate:
- expected symbols > 0
- successful symbol downloads / expected symbols >= 95%
- no unexplained shard loss
- PIT manifest provenance retained
- failed symbols explicitly listed
- empty historical periods remain distinguishable from transport/API failure

This source gate still does **not** by itself make the canonical replay PASS.
Market/sector/decision/outcome/execution context must still be joined and audited.

## Operational note

The current repository already references `secrets.FUGLE_API_KEY` in the existing historical-export workflow.
No new secret name is introduced.

The whole-universe workflow is manual-only because it can be long-running and data-heavy.

## Next machine-executable step

Run:
`W3A Whole-Universe PIT Intraday History`

with the governed period:
- from: 2023-05-23
- to: latest intended research cutoff

After all 20 shard artifacts finish, aggregate shard summaries and verify the >=95% source-coverage gate.

## Production impact
NONE.
