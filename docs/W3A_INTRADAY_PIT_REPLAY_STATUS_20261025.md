# W3A｜Intraday PIT Historical Replay Dataset — Build Status 2026-10-25

## Current status
**PARTIAL COMPLETE / DATA_BLOCKED**

This update builds the canonical replay assembly layer required by W2, without changing Production trading logic.

## Completed
1. Canonical W2 replay contract already exists:
   - `research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md`
2. W2 fail-closed validator already exists:
   - `research/intraday_replay_validator.py`
3. W2 validation runner already exists:
   - `research/w2_intraday_validation_runner.py`
4. 2023+ PIT historical universe gate is already PASS.
5. New W3A replay builder added:
   - `research/build_intraday_pit_replay.py`
6. Builder outputs:
   - `intraday_pit_replay.csv`
   - `intraday_pit_replay_manifest.json`
   - `intraday_pit_replay_gap_report.json`
7. Builder automatically:
   - attaches point-in-time universe membership;
   - preserves effective dates/source;
   - runs standardized DQ;
   - runs W2 fail-closed replay validation;
   - emits `PASS` or `DATA_BLOCKED`;
   - never changes Production.
8. CI integration added:
   - `.github/workflows/test-w3a-intraday-pit-replay.yml`

## Current hard blocker

The code path is now available, but a promotion-grade replay dataset still requires concrete historical decision-time inputs.

Missing/unfinished evidence domains:
- historical candidate decision snapshots for all eligible candidates, not winners only;
- complete market context frozen at each decision timestamp;
- effective-dated sector mapping + sector RS price history;
- Phase / Anti-Chase decision-time features;
- frozen 10-rule outputs from Production v1.4 definitions;
- execution context / historical spread-slippage evidence where available;
- outcome join with 0.45% and 0.65% cost scenarios.

The existing Fugle downloader provides historical 5-minute candles, but candles alone are insufficient to claim a complete replay dataset.

## Governance consequence

Until the real dataset passes:
- PIT universe >= 95%
- market context >= 95%
- sector mapping/RS >= 95% where claimed
- Phase / Anti-Chase >= 95%
- outcome completeness >= 95%
- cost completeness = 100%
- leakage audit = PASS

the formal status remains:

`W2 = HOLD / DATA_BLOCKED`

No Full Model expectancy, Rule Contribution, Stable Rule or Production promotion may be claimed.

## Next machine-executable step

Feed a normalized historical decision snapshot CSV plus the canonical PIT universe interval JSON into:

```bash
python research/build_intraday_pit_replay.py \
  --decisions <decision_snapshot.csv> \
  --pit-universe <pit_universe_intervals.json> \
  --out-dir research_output/w3a_intraday_pit
```

Then, only if the manifest reports PASS:

```bash
python research/w2_intraday_validation_runner.py \
  --dataset research_output/w3a_intraday_pit/intraday_pit_replay.csv
```

## Production impact
NONE.
