# W1｜Sky Swing Challenger V1.1 — Frozen Exact-Rule Specification

- Date frozen: 2026-10-26
- Status: PREREGISTERED_CHALLENGER
- Production impact: NONE
- Production baseline remains: Sky Swing V1.0 ACTIVE / unchanged
- Purpose: create one fully reproducible Swing rule set for clean canonical PIT validation without pretending to reconstruct V1.0.

## 1. Universe / direction
- Taiwan TWSE + TPEx canonical PIT universe only.
- Long only.
- New-entry price at execution open must be < TWD 100.
- Missing/invalid bars fail closed.
- No forward fill across non-trading / pre-listing / post-delisting periods.

## 2. Decision / execution causality
- All features are computed using data available through signal date D close.
- Entry occurs at D+1 open.
- No D+1 high/low/close may participate in signal construction.
- Corporate-action adjusted PIT-safe daily bars are required.

## 3. Market Gate
At signal date D:
- cross-sectional breadth = fraction of eligible PIT symbols with close > MA20.
- PASS when breadth >= 0.50.

This threshold is frozen before canonical replay results.

## 4. Trend Gate
For the stock at D:
- close > MA20
- MA20 > MA60

Both required.

## 5. Relative Strength Gate
- 20-trading-day return is ranked cross-sectionally among eligible PIT symbols on D.
- PASS when percentile rank >= 0.70.

## 6. Setup + Trigger
Breakout setup/trigger is fully end-of-day and causal:
- prior_20d_high = maximum high over D-20 through D-1.
- Trigger PASS when close(D) > prior_20d_high.
- Entry reference = D+1 open.

No intraday trigger reconstruction is used.

## 7. Anti-Chase
At D:
- close / MA20 - 1 <= 0.08.
- D daily range / close <= 0.08.

Both required.
If either fails: no entry.

## 8. Initial stop
At entry day E=D+1:
- initial_stop = signal-day low(D).
- Entry is rejected if initial_stop >= entry_open.
- No widening after entry.

Risk per share = entry_open - initial_stop.

## 9. RR Gate
- FIXED_3R reference target = entry_open + 3 * risk_per_share.
- Gross planned RR = 3.0.
- Candidate must remain valid after 0.45% and 0.65% round-trip cost analysis.
- Cost analysis is evaluation-time only; it does not change entry thresholds.

## 10. Add rule
- Disabled for this Challenger validation.
- No averaging down.
- No pyramiding.
This isolates the entry/exit edge before testing add logic in any future separately preregistered candidate.

## 11. Exit variants
Hard stop is active for every variant and always takes precedence on same-day stop/target ambiguity.

### FIXED_3R
- stop = initial_stop.
- target = entry + 3R.
- If day low <= stop and high >= target on same bar, assume STOP FIRST.
- If neither occurs, exit at close on holding day 20.

### MA20_TRAIL
- Day 1 hard stop = initial_stop.
- From holding day 2 onward:
  trail_stop = max(initial_stop, prior trading day's MA20).
- Exit when current low <= trail_stop.
- If open < trail_stop, fill at open; otherwise at trail_stop.
- Maximum holding = 20 trading days; exit at day-20 close.

### SWING10_TRAIL
- Day 1 hard stop = initial_stop.
- From holding day 2 onward:
  swing10 = minimum low of the 10 completed trading days ending on prior day.
  trail_stop = max(initial_stop, swing10).
- Exit when current low <= trail_stop.
- If open < trail_stop, fill at open; otherwise at trail_stop.
- Maximum holding = 20 trading days; exit at day-20 close.

## 12. Portfolio validation
Signal-level replay is primary.
Portfolio layer is separately reported with:
- max concurrent positions = 5
- equal 1R risk units
- first valid signals by descending RS percentile, then symbol
- no duplicate symbol overlap
- no new position while symbol is already held
- no averaging down
- portfolio heat cap = 5R

No user-specific currency sizing is inferred.

## 13. Fixed costs
Mandatory:
- 0.45% round trip
- 0.65% stress round trip

## 14. Required outputs
For each exit and cost:
- sample count
- win rate
- avg win / avg loss
- Expectancy %
- Profit Factor
- Expectancy R
- Max Drawdown in cumulative R
- yearly
- Bull / Neutral / Bear
- >=3 time-ordered walk-forward folds
- portfolio constrained metrics

## 15. Governance
- No threshold, horizon, stop, target, feature or ranking changes after first canonical result is visible.
- Any later change is a new version and requires new preregistration.
- A positive backtest does not authorize Production.
- Final W1 status only: PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE.
