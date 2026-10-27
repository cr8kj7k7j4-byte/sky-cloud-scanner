# W1｜Sky Swing Challenger V1.1 Intraday Execution Overlay v1.0

- Date frozen: 2026-10-27
- Status: PREREGISTERED_EXECUTION_OVERLAY
- Production impact: NONE
- Base strategy: Sky Swing Challenger V1.1
- Purpose: allow intraday execution judgment without changing the frozen V1.1 D-close signal logic.

## 1. Boundary

This overlay does not change:
- Market Gate
- Trend Gate
- RS Gate
- Breakout Trigger
- Anti-Chase
- initial stop
- original D+1 open reference
- original 3R reference target
- ranking order

It only decides whether the current intraday price is still no worse than the original D+1 open execution reference.

## 2. Exact intraday decision

For a candidate that already passed the frozen V1.1 signal on D close:

- original_entry = actual D+1 session open
- original_stop = signal-day low(D)
- original_target = original_entry + 3 * (original_entry - original_stop)

At any intraday observation:

### BUY_ELIGIBLE
All must be true:
1. current_price is available
2. current_price > original_stop
3. current_price <= original_entry
4. current_price < original_target

Interpretation: current execution price is no worse than the original D+1 open reference. No chase.

### WAIT
- current_price > original_entry
- current_price < original_target
- current_price > original_stop

Interpretation: price is above the frozen entry reference. Wait for a pullback to original_entry or lower. Do not chase.

### REJECT_STOPPED
- current_price <= original_stop

Interpretation: original invalidation level has already failed. No new entry.

### REJECT_TARGET_PASSED
- current_price >= original_target

Interpretation: the original 3R reference target has already been reached or exceeded. Entry opportunity is considered missed.

### DATA_BLOCKED
- current_price or original_entry is missing

No decision may be synthesized.

## 3. Highest acceptable price

highest_acceptable_price = original_entry

No additional percentage buffer, tick buffer, ATR buffer, or discretionary tolerance is allowed.

## 4. Governance

- This is an execution overlay, not a new Alpha rule.
- Historical V1.1 backtest results must not be relabeled as evidence for this overlay.
- Overlay performance must be tracked separately if used for research.
- No real-money automation is authorized.
- Any future relaxation above original_entry requires a new preregistration and separate validation.
