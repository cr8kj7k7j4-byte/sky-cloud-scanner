from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import (
    EXEC_COST_PROFILE,
    EXEC_ENTRY_SLIPPAGE_BPS,
    EXEC_EXIT_SLIPPAGE_BPS,
    EXEC_SPREAD_BPS,
    EXEC_LIQUIDITY_PENALTY_BPS,
    EXEC_FINANCING_INTEREST_PER_SHARE,
)
from src.cost_profiles import get_observed_cost_profile
from src.fugle import get_candles
from src.outcome_engine import (
    evaluate_ranking_outcome,
    evaluate_shadow_long_path,
)

TZ = ZoneInfo("Asia/Taipei")
LEDGER_ACTIVATED_AT = datetime.fromisoformat("2026-10-24T23:28:08+00:00")


def _parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def load_paper_records(root, trade_date):
    root = Path(root)
    records = []
    files = sorted(
        path
        for path in root.rglob("*.json")
        if "paper" in {part.lower() for part in path.parts}
    )
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            observed = _parse_dt(row.get("observed_at"))
            if observed is None:
                continue
            if observed.date().isoformat() != trade_date:
                continue
            records.append(dict(row))
    return records, files


def bars_after_observation(candles, observed_at):
    observed = _parse_dt(observed_at)
    if observed is None:
        return []
    out = []
    rows = candles.get("data", []) if isinstance(candles, dict) else []
    for bar in rows:
        if not isinstance(bar, dict):
            continue
        bar_time = _parse_dt(bar.get("date"))
        if bar_time is None or bar_time <= observed:
            continue
        out.append(dict(bar))
    return out


def _execution_cost_inputs():
    profile = get_observed_cost_profile(EXEC_COST_PROFILE)
    if profile is None:
        return {
            "fee_rate": None,
            "tax_rate": None,
            "entry_impact_rate": None,
            "exit_impact_rate": None,
            "reason": "EXEC_COST_PROFILE_NOT_FOUND",
        }

    required = (
        EXEC_ENTRY_SLIPPAGE_BPS,
        EXEC_EXIT_SLIPPAGE_BPS,
        EXEC_SPREAD_BPS,
        EXEC_LIQUIDITY_PENALTY_BPS,
    )
    complete = all(x is not None for x in required)

    if (
        profile.transaction_mode == "MARGIN_FINANCING"
        and EXEC_FINANCING_INTEREST_PER_SHARE is None
    ):
        complete = False
        reason = "FINANCING_INTEREST_REQUIRED"
    else:
        reason = None if complete else "EXECUTION_IMPACT_INPUT_REQUIRED"

    if complete:
        spread_half = float(EXEC_SPREAD_BPS) / 2.0
        entry_bps = (
            float(EXEC_ENTRY_SLIPPAGE_BPS)
            + spread_half
            + float(EXEC_LIQUIDITY_PENALTY_BPS)
        )
        exit_bps = (
            float(EXEC_EXIT_SLIPPAGE_BPS)
            + spread_half
            + float(EXEC_LIQUIDITY_PENALTY_BPS)
        )
        entry_impact_rate = entry_bps / 10000.0
        exit_impact_rate = exit_bps / 10000.0
    else:
        entry_impact_rate = None
        exit_impact_rate = None

    return {
        "profile_id": profile.profile_id,
        "transaction_mode": profile.transaction_mode,
        "fee_rate": profile.buy_commission_rate,
        "tax_rate": profile.sell_tax_rate,
        "entry_impact_rate": entry_impact_rate,
        "exit_impact_rate": exit_impact_rate,
        "reason": reason,
    }


def _strategy_eligible(record):
    strategy = dict(record.get("strategy") or {})
    risk = dict(record.get("risk") or {})
    monitor = dict(record.get("monitor") or {})
    return bool(
        monitor.get("state") == "TRIGGERED"
        and risk.get("status") == "ALLOW"
        and strategy.get("trigger") is not None
        and strategy.get("stop") is not None
        and strategy.get("target") is not None
    )


def backfill_record(record, candles, cost_inputs):
    out = dict(record)
    future_bars = bars_after_observation(candles, record.get("observed_at"))
    market = dict(record.get("market") or {})
    reference = market.get("last")

    ranking = evaluate_ranking_outcome(
        reference_price=reference,
        bars=future_bars,
    )

    strategy_result = {
        "status": "NOT_ELIGIBLE",
        "outcome_type": "COUNTERFACTUAL_SHADOW",
        "reason": (
            "Requires monitor=TRIGGERED, risk=ALLOW, and explicit "
            "trigger/stop/target."
        ),
        "research_only": True,
    }

    if _strategy_eligible(record):
        strategy = dict(record.get("strategy") or {})
        strategy_result = evaluate_shadow_long_path(
            entry=strategy.get("trigger"),
            stop=strategy.get("stop"),
            target=strategy.get("target"),
            bars=future_bars,
            fee_rate=cost_inputs.get("fee_rate"),
            tax_rate=cost_inputs.get("tax_rate"),
            entry_impact_rate=cost_inputs.get("entry_impact_rate"),
            exit_impact_rate=cost_inputs.get("exit_impact_rate"),
        )
        strategy_result["execution_cost_profile"] = cost_inputs.get(
            "profile_id"
        )
        if (
            strategy_result.get("status") == "COST_INPUT_REQUIRED"
            and cost_inputs.get("reason")
        ):
            strategy_result["cost_input_reason"] = cost_inputs["reason"]

    out["outcome"] = {
        "status": ranking.get("status"),
        "outcome_type": "SHADOW_EVIDENCE",
        "backfilled_at": datetime.now(TZ).isoformat(),
        "ranking": ranking,
        "strategy_counterfactual": strategy_result,
        "research_only": True,
        "note": (
            "Ranking outcome is observational forward evidence. "
            "Strategy outcome, when present, is counterfactual and not an "
            "actual fill or realized P&L."
        ),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-root", default="shadow_history")
    ap.add_argument("--trade-date")
    ap.add_argument("--out-dir", default="output/paper")
    args = ap.parse_args()

    trade_date = args.trade_date or datetime.now(TZ).date().isoformat()
    records, files = load_paper_records(args.paper_root, trade_date)

    symbols = sorted(
        {
            str(row.get("symbol") or "")
            for row in records
            if row.get("symbol")
        }
    )
    candle_cache = {}
    candle_errors = {}
    for symbol in symbols:
        try:
            candle_cache[symbol] = get_candles(symbol, "5")
        except Exception as exc:
            candle_errors[symbol] = f"{type(exc).__name__}: {exc}"
            candle_cache[symbol] = {}

    costs = _execution_cost_inputs()
    enriched = []
    for row in records:
        symbol = str(row.get("symbol") or "")
        item = backfill_record(row, candle_cache.get(symbol, {}), costs)
        if symbol in candle_errors:
            item["outcome"]["ranking"] = {
                "status": "DATA_SOURCE_ERROR",
                "outcome_type": "RANKING_SHADOW",
                "reason": candle_errors[symbol],
                "research_only": True,
            }
            item["outcome"]["status"] = "DATA_SOURCE_ERROR"
        enriched.append(item)

    payload = {
        "schema_version": "1.1",
        "trade_date": trade_date,
        "source_files_scanned": len(files),
        "records_found": len(records),
        "unique_symbols": len(symbols),
        "candle_errors": candle_errors,
        "execution_cost_inputs": costs,
        "records": enriched,
    }

    out = Path(args.out_dir) / f"{trade_date}-outcomes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
