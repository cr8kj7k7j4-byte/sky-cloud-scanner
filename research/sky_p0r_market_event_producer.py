"""Research-only observed-bar PAPER_ONLY event producer.

Consumes *existing* externally captured, completed market bars. It never fetches
quotes, places orders or asserts broker fills. All estimates remain unverified
until their source Artifact/run/SHA has been independently read back.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import math

from src.cost_profiles import USER_CASH_DAYTRADE_20261022
from research.sky_p0r_order_gate import evaluate_paper_order
from research.sky_p0r_paper_event_replay import replay
from research.sky_p0r_paper_ledger_readback import audit_paper_ledger


def _time(value):
    if not isinstance(value, str):
        raise ValueError("TIME_REQUIRED")
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("BAD_TIME") from exc
    if value.utcoffset() is None:
        raise ValueError("AWARE_TIME_REQUIRED")
    return value


def _price(value):
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or value <= 0):
        raise ValueError("BAD_PRICE")
    return float(value)


def produce(payload):
    """One existing signal, next completed candle open, next-open exit estimate.

    Stop/target are observed from an *already completed* subsequent bar. Exit is
    estimated at the *following* completed bar's open (not the stop price).
    No open-only inference if the downstream bar is missing; fail closed.
    """
    if not isinstance(payload, dict):
        raise ValueError("SOURCE_PAYLOAD_REQUIRED")
    context = payload.get("context")
    signal = payload.get("signal")
    bars = payload.get("completed_bars")
    if not isinstance(context, dict) or not isinstance(signal, dict) or not isinstance(bars, list):
        raise ValueError("CONTEXT_SIGNAL_COMPLETED_BARS_REQUIRED")
    for k in ("run_id", "scan_id", "source_artifact", "simulator_version"):
        if not isinstance(context.get(k), str) or not context[k]:
            raise ValueError("CONTEXT_PROVENANCE_REQUIRED")
    if signal.get("market_scan_id") != context["scan_id"]:
        raise ValueError("SIGNAL_SCAN_MISMATCH")
    signal_at = _time(signal.get("signal_time"))
    observed_at = _time(context.get("observed_at"))
    if observed_at < signal_at or signal_at.date() != observed_at.date():
        raise ValueError("SIGNAL_TIME_INVALID")
    symbol = signal.get("symbol")
    signal_id = signal.get("signal_id")
    candidate = signal.get("candidate")
    assumptions = signal.get("execution_assumptions")
    if not isinstance(symbol, str) or not symbol or not isinstance(signal_id, str) or not signal_id:
        raise ValueError("SIGNAL_IDENTITY_MISSING")
    if not isinstance(candidate, dict) or not isinstance(assumptions, dict):
        raise ValueError("PLAN_COST_MISSING")
    entry = _price(candidate.get("entry"))
    stop = _price(candidate.get("stop"))
    target = _price(candidate.get("target"))
    if not stop < entry < target:
        raise ValueError("INVALID_LONG_PLAN")
    normalized = []
    seen = set()
    previous = None
    for bar in bars:
        if not isinstance(bar, dict) or bar.get("symbol") != symbol or bar.get("source_type") != "MARKET_OBSERVATION":
            raise ValueError("UNSUPPORTED_BAR_PROVENANCE")
        t = _time(bar.get("completed_at"))
        opened_at = _time(bar.get("started_at"))
        if opened_at >= t or (previous is not None and opened_at < previous):
            raise ValueError("OVERLAPPING_OR_NONCAUSAL_BAR")
        if t in seen or (previous is not None and t <= previous):
            raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_BARS")
        seen.add(t)
        previous = t
        if t > observed_at or t.date() != observed_at.date() or bar.get("source_artifact") != context["source_artifact"]:
            raise ValueError("BAR_SOURCE_TIME_MISMATCH")
        o,h,l,c = (_price(bar.get(k)) for k in ("open", "high", "low", "close"))
        if l > min(o,c) or h < max(o,c) or l > h:
            raise ValueError("INVALID_OHLC")
        normalized.append((opened_at,t,o,h,l,c))
    # A completed bar after signal is needed for the first estimated entry.
    eligible = [i for i,(start_at,_,_,_,_,_) in enumerate(normalized) if start_at > signal_at]
    if len(eligible) < 3:
        return {"verdict": "INSUFFICIENT_FUTURE_COMPLETED_BARS", "events": [],
                "snapshot": None, "closed_fills": [],
                "production_eligible": False, "market_source_independently_verified": False}
    start = eligible[0]
    if start + 2 >= len(normalized):
        raise ValueError("NEXT_OPEN_EXIT_NOT_OBSERVED")
    # Bar is completed; its OPEN is only a retrospective simulated fill estimate.
    entry_t, _, opened, _, _, _ = normalized[start]
    # Entry price must match the precommitted risk decision; never silently chase.
    if abs(opened-entry) > 1e-8:
        return {"verdict": "ENTRY_PRICE_NOT_EXECUTABLE_AS_PLANNED",
                "events": [], "snapshot": None, "closed_fills": [],
                "production_eligible": False, "market_source_independently_verified": False}
    # Only a later *completed* bar may trigger exit. Do not use entry candle extremes.
    trigger = None
    for i in range(start+1, len(normalized)-1):
        _,_,_,high,low,_ = normalized[i]
        if low <= stop:
            trigger = (i, "STOP")
            break
        if high >= target:
            trigger = (i, "TARGET")
            break
    if trigger is None:
        return {"verdict": "OPEN_TRADE_WITHOUT_COMPLETED_EXIT_EVIDENCE",
                "events": [], "snapshot": None, "closed_fills": [],
                "production_eligible": False, "market_source_independently_verified": False}
    exit_i, reason = trigger
    exit_t, _, exit_price,_,_,_ = normalized[exit_i+1]
    p = USER_CASH_DAYTRADE_20261022
    shares = signal.get("shares")
    if not isinstance(shares,int) or isinstance(shares,bool) or shares<=0:
        raise ValueError("SHARES_REQUIRED")
    # Require explicit, nonzero research execution-cost assumptions;
    # BPS are not inferred from OHLC bars or historical brokerage fees.
    for field in ("entry_slippage_bps", "exit_slippage_bps", "spread_bps",
                  "liquidity_penalty_bps"):
        val=assumptions.get(field)
        if not isinstance(val,(int,float)) or isinstance(val,bool) or not math.isfinite(val) or val<0:
            raise ValueError("EXECUTION_COST_ASSUMPTIONS_REQUIRED")
    # Do not double count modeled slippage in entry/exit prices; explicit
    # monetary charge is an adverse estimate, not a claim of actual fill.
    slip = (entry*assumptions["entry_slippage_bps"]+
            exit_price*assumptions["exit_slippage_bps"])*shares/10000
    spread=(entry+exit_price)*assumptions["spread_bps"]*shares/20000
    liquidity=(entry+exit_price)*assumptions["liquidity_penalty_bps"]*shares/10000
    order = {"kind":"ORDER","event_id":"entry-order","order_id":"paper-entry",
             "side":"BUY","event_time":signal_at.isoformat(),
             "market_scan_id":context["scan_id"],"symbol":symbol,
             "signal_id":signal_id,"risk_status":"ALLOW",
             "candidate":candidate,"execution_assumptions":assumptions}
    gate=evaluate_paper_order(order,cash=500000,equity=500000,positions={},
                              realized_net=0,consecutive_stops=0,
                              observed_at=signal_at.isoformat())
    if gate.get("status")!="ALLOW" or shares>gate.get("recommended_shares",0):
        return {"verdict":"CANONICAL_P0R_P0X_BLOCK","events":[],
                "snapshot":None,"closed_fills":[],"production_eligible":False,
                "market_source_independently_verified":False}
    events=[order,
        {"kind":"FILL","event_id":"entry-fill","order_id":"paper-entry",
         "event_time":entry_t.isoformat(),"market_scan_id":context["scan_id"],
         "price":entry,"shares":shares,"fee_twd":round(entry*shares*p.buy_commission_rate,4),
         "original_stop":stop,"market_data_time":signal_at.isoformat(),
         "fill_assumption":"NEXT_BAR_OPEN_ESTIMATE"},
        {"kind":"ORDER","event_id":"exit-order","order_id":"paper-exit","side":"SELL",
         "event_time":normalized[exit_i][1].isoformat(),
         "market_scan_id":context["scan_id"],"symbol":symbol,"signal_id":signal_id},
        {"kind":"FILL","event_id":"exit-fill","order_id":"paper-exit",
         "event_time":exit_t.isoformat(),"market_scan_id":context["scan_id"],
         "price":exit_price,"shares":shares,
         "fee_twd":round(exit_price*shares*p.sell_commission_rate,4),
         "sale_tax_twd":round(exit_price*shares*p.sell_tax_rate,4),
         "slippage_estimate_twd":round(slip,4),
         "spread_estimate_twd":round(spread,4),
         "liquidity_impact_estimate_twd":round(liquidity,4),
         "fill_assumption":"NEXT_BAR_OPEN_ESTIMATE","reason":reason}]
    snapshot,closed=replay(events,**context)
    audit=audit_paper_ledger(snapshot,closed)
    if not audit["reconciled"]:
        raise ValueError("EVENT_TO_LEDGER_RECONCILIATION_FAILED")
    return {"verdict":"PAPER_EVENT_CHAIN_RECONCILED_ORIGIN_UNVERIFIED",
            "events":events,"snapshot":snapshot,"closed_fills":closed,
            "ledger_audit":audit,"production_eligible":False,
            "market_source_independently_verified":False,
            "simulated_fill_origin_independently_verified":False}


def main():
    base=Path("output/sky_paper_runtime")
    source=base/"completed_market_evidence.json"
    if not source.is_file():
        status={"schema":"SKY_P0R_PAPER_MARKET_SOURCE_STATUS_V1",
                "verdict":"INSUFFICIENT_DATA",
                "reason":"RAW_COMPLETED_OHLC_WITH_SOURCE_AND_APPROVED_SIGNAL_MISSING",
                "input_path":str(source),
                "source_artifact_verified":False,
                "paper_events_produced":0,
                "production_eligible":False}
        output=Path("output/sky_p0r_paper_ledger_readback")
        output.mkdir(parents=True,exist_ok=True)
        (output/"market_source_status.json").write_text(
            json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(status))
        return 0
    report=produce(json.loads(source.read_text(encoding="utf-8")))
    if report["snapshot"] is not None:
        # never generate events from test fixtures in CI; only an explicit
        # market evidence file may activate the source adapter.
        base.mkdir(parents=True,exist_ok=True)
        (base/"events.json").write_text(json.dumps({
            "events":report["events"],
            "context":{k:report["snapshot"][k] for k in (
                "run_id","scan_id","observed_at","source_artifact","simulator_version")}
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    status={"schema":"SKY_P0R_PAPER_MARKET_SOURCE_STATUS_V1",
            "verdict":report["verdict"], "source_artifact_verified":False,
            "paper_events_produced":len(report["events"]),
            "production_eligible":False}
    output=Path("output/sky_p0r_paper_ledger_readback")
    output.mkdir(parents=True,exist_ok=True)
    (output/"market_source_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(status))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
