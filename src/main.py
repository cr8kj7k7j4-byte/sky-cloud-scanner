from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json

from .config import (
    TOP_N, DEEP_DIVE_N, STRICT_OFFICIAL_MODE, ALLOW_MIS_OTC_FALLBACK,
    ACCOUNT_EQUITY, RISK_PER_TRADE_PCT, DAILY_LOSS_LIMIT_PCT,
    MAX_PORTFOLIO_HEAT_PCT, MAX_POSITION_PCT, CORRELATION_LIMIT_PCT,
    MAX_CONCURRENT_POSITIONS, CAUTION_LOSS_STREAK, DEFENSIVE_LOSS_STREAK,
    LOCKDOWN_DRAWDOWN_PCT, LOT_SIZE, DAILY_PNL, OPEN_RISK,
    CONCURRENT_POSITIONS, CORRELATED_OPEN_RISK, ACCOUNT_DRAWDOWN_PCT,
    CONSECUTIVE_LOSSES, MONITOR_STATE_BACKEND, REDIS_URL,
    MONITOR_STATE_REDIS_KEY, PREMARKET_REDIS_KEY,
    EXEC_BUY_COMMISSION_RATE, EXEC_SELL_COMMISSION_RATE, EXEC_SELL_TAX_RATE,
    EXEC_ENTRY_SLIPPAGE_BPS, EXEC_EXIT_SLIPPAGE_BPS, EXEC_SPREAD_BPS,
    EXEC_LIQUIDITY_PENALTY_BPS, EXEC_FILL_PROBABILITY,
    EXEC_FINANCING_INTEREST_PER_SHARE, EXEC_COST_PROFILE, EXEC_MIN_RR,
    EXEC_ENFORCE_GATE, PAPER_TRADING_MODE, P0S_OOS_VERDICT, PAPER_GCS_BUCKET,
)
from .official import load_official_universe, fetch_mis_quotes
from .fugle import get_ticker, get_quote, get_candles
from .sky_rules import first_gate, score_for_ranking, enrich
from .notifier import send_telegram
from .risk_engine import RiskPolicy, evaluate_candidate, drawdown_state
from .execution_engine import ExecutionCostPolicy
from .cost_profiles import get_observed_cost_profile
from .feature_engine import build_features
from .regime_engine import detect_regime
from .ml_layer import baseline_model_predictions, ensemble
from .explainability import explain
from .validation import evaluate_validation_gate
from .knowledge_engine import (
    market_evidence_from_candidate,
    build_evidence_ledger as build_knowledge_evidence_ledger,
)
from .agent_orchestrator import orchestrate
from .research_sources import source_health_template
from .market_intelligence import summarize_market
from .relative_strength import apply_relative_strength
from .event_risk import assess_event_risk
from .evidence_ledger import build_evidence_ledger as build_structured_evidence_ledger
from .strategy_builder import build_breakout_plan, apply_plan
from .monitor_engine import evaluate_monitor_state
from .state_store import MonitorStateStore
from .premarket_state import load_premarket_event_snapshot
from .paper_trading import (
    evaluate_paper_gate,
    build_paper_snapshot,
    write_paper_run_file,
    upload_paper_run_to_gcs,
)

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output")
MONITOR_STATE_FILE = OUT / "monitor_state.json"

RISK_STATUS_ZH = {
    "ALLOW": "允許進場",
    "BLOCK": "禁止進場",
    "RISK_INPUT_REQUIRED": "風控資料不足",
}
RISK_STATE_ZH = {
    "NORMAL": "正常",
    "CAUTION": "警戒",
    "DEFENSIVE": "防守",
    "LOCKDOWN": "鎖定",
}

def _risk_policy():
    return RiskPolicy(
        risk_per_trade_pct=RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=DAILY_LOSS_LIMIT_PCT,
        max_portfolio_heat_pct=MAX_PORTFOLIO_HEAT_PCT,
        max_position_pct=MAX_POSITION_PCT,
        correlation_limit_pct=CORRELATION_LIMIT_PCT,
        max_concurrent_positions=MAX_CONCURRENT_POSITIONS,
        caution_loss_streak=CAUTION_LOSS_STREAK,
        defensive_loss_streak=DEFENSIVE_LOSS_STREAK,
        lockdown_drawdown_pct=LOCKDOWN_DRAWDOWN_PCT,
        lot_size=LOT_SIZE,
    )

def _execution_policy():
    profile = get_observed_cost_profile(EXEC_COST_PROFILE)

    profile_buy = profile.buy_commission_rate if profile else None
    profile_sell = profile.sell_commission_rate if profile else None
    profile_tax = profile.sell_tax_rate if profile else None

    policy = ExecutionCostPolicy(
        buy_commission_rate=(
            EXEC_BUY_COMMISSION_RATE
            if EXEC_BUY_COMMISSION_RATE is not None else profile_buy
        ),
        sell_commission_rate=(
            EXEC_SELL_COMMISSION_RATE
            if EXEC_SELL_COMMISSION_RATE is not None else profile_sell
        ),
        sell_tax_rate=(
            EXEC_SELL_TAX_RATE
            if EXEC_SELL_TAX_RATE is not None else profile_tax
        ),
        entry_slippage_bps=EXEC_ENTRY_SLIPPAGE_BPS,
        exit_slippage_bps=EXEC_EXIT_SLIPPAGE_BPS,
        spread_bps=EXEC_SPREAD_BPS,
        liquidity_penalty_bps=EXEC_LIQUIDITY_PENALTY_BPS,
        fill_probability=EXEC_FILL_PROBABILITY,
        financing_interest_per_share=EXEC_FINANCING_INTEREST_PER_SHARE,
        require_financing_interest=(
            profile is not None and profile.transaction_mode == "MARGIN_FINANCING"
        ),
        min_execution_rr=EXEC_MIN_RR,
        enforce_gate=EXEC_ENFORCE_GATE,
    )
    return policy


def _portfolio_context():
    return {
        "account_equity": ACCOUNT_EQUITY,
        "daily_pnl": DAILY_PNL,
        "open_risk": OPEN_RISK,
        "concurrent_positions": CONCURRENT_POSITIONS,
        "correlated_open_risk": CORRELATED_OPEN_RISK,
        "drawdown_pct": ACCOUNT_DRAWDOWN_PCT,
        "consecutive_losses": CONSECUTIVE_LOSSES,
        "execution_policy": _execution_policy(),
    }

def run():
    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%dT%H%M%S%z")
    OUT.mkdir(exist_ok=True)
    paper_gate = evaluate_paper_gate(PAPER_TRADING_MODE, P0S_OOS_VERDICT)

    state_store = MonitorStateStore(
        MONITOR_STATE_BACKEND,
        file_path=MONITOR_STATE_FILE,
        redis_url=REDIS_URL,
        redis_key=MONITOR_STATE_REDIS_KEY,
    )
    previous_monitor_state = state_store.load()

    policy = _risk_policy()
    portfolio_context = _portfolio_context()
    portfolio_state = drawdown_state(
        ACCOUNT_DRAWDOWN_PCT, CONSECUTIVE_LOSSES, policy
    )

    st = {
        "run_time": now.isoformat(),
        "version": "0.4",
        "full_market_scan": False,
        "strict_official_mode": STRICT_OFFICIAL_MODE,
        "warnings": [],
        "source_health": {},
        "market_intelligence": {},
        "event_risk": {},
        "premarket_event_snapshot": {},
        "monitor_engine": {
            "enabled": True,
            "backend": state_store.backend,
            "persistent": state_store.persistent,
            "health": state_store.health(),
            "previous_count": len(previous_monitor_state),
            "decisions": [],
            "transitions": [],
        },
        "top100": [],
        "deep": [],
        "deep_rejected": [],
        "deep_unverified": [],
        "ml_foundation": {
            "enabled": True,
            "mode": "RESEARCH_ONLY",
            "production_eligible": False,
        },
        "knowledge_engine": {"enabled": True, "mode": "EVIDENCE_FIRST", "research_sources": source_health_template()},
        "agent_orchestration": {"enabled": True, "single_agent_can_trade": False},
        "paper_trading": {
            **paper_gate.to_dict(),
            "gcs_bucket_configured": bool(PAPER_GCS_BUCKET),
            "records": 0,
            "ledger_upload": None,
        },
        "execution_engine": {
            "enabled": True,
            "profile_id": EXEC_COST_PROFILE,
            "profile": (
                get_observed_cost_profile(EXEC_COST_PROFILE).to_dict()
                if get_observed_cost_profile(EXEC_COST_PROFILE)
                else None
            ),
            "gate_enforced": EXEC_ENFORCE_GATE,
            "min_execution_rr": EXEC_MIN_RR,
            "cost_inputs_complete": all(v is not None for v in (
                _execution_policy().buy_commission_rate,
                _execution_policy().sell_commission_rate,
                _execution_policy().sell_tax_rate,
                EXEC_ENTRY_SLIPPAGE_BPS,
                EXEC_EXIT_SLIPPAGE_BPS,
                EXEC_SPREAD_BPS,
                EXEC_LIQUIDITY_PENALTY_BPS,
            )),
        },
        "risk_engine": {
            "enabled": True,
            "policy": policy.to_dict(),
            "portfolio_context": portfolio_context,
            "state": portfolio_state,
            "state_zh": RISK_STATE_ZH.get(portfolio_state, portfolio_state),
        },
    }

    try:
        universe, ust = load_official_universe()
        st["source_health"]["official_universe"] = ust
        st["universe_count"] = len(universe)

        rows, miswarn = fetch_mis_quotes(universe)
        st["warnings"].extend(miswarn)
        st["mis_quote_count"] = len(rows)

        twse_rows = [x for x in rows if x["exchange"] == "TWSE"]
        otc_rows = [x for x in rows if x["exchange"] == "TPEx"]

        official_universe_ok = ust["twse"] >= 500 and ust["tpex"] >= 400
        twse_intraday_ok = len(twse_rows) >= 400

        # Free/public TPEx official full-market real-time feed is not certified
        # in this build. MIS OTC can be used operationally but cannot promote
        # strict full-market status.
        tpex_official_intraday_ok = False

        st["source_health"]["twse_intraday"] = {
            "ok": twse_intraday_ok,
            "source": "TWSE MIS",
            "count": len(twse_rows),
        }
        st["source_health"]["tpex_intraday"] = {
            "ok": False,
            "source": (
                "TPEx official public/free full-market real-time feed "
                "not certified; TWSE MIS OTC is operational fallback only"
            ),
            "fallback_count": len(otc_rows),
        }

        if STRICT_OFFICIAL_MODE:
            st["full_market_scan"] = bool(
                official_universe_ok
                and twse_intraday_ok
                and tpex_official_intraday_ok
            )
            if not st["full_market_scan"]:
                st["warnings"].append(
                    "未完成全市場掃描：TPEx 官方免費公開來源未能驗證完整盤中"
                    "全市場即時資料鏈；候選最高只列 A。"
                )
        else:
            st["full_market_scan"] = bool(
                official_universe_ok and len(rows) >= 700
            )

        working_rows = rows if ALLOW_MIS_OTC_FALLBACK else twse_rows
        st["market_intelligence"] = summarize_market(working_rows)

        premarket_state = load_premarket_event_snapshot(
            redis_url=REDIS_URL,
            redis_key=PREMARKET_REDIS_KEY,
        )
        snapshot = premarket_state.get("snapshot") or {}
        snapshot_events = snapshot.get("events") or []
        st["premarket_event_snapshot"] = {
            "ok": premarket_state.get("ok", False),
            "source": premarket_state.get("source"),
            "reason": premarket_state.get("reason"),
            "generated_at": snapshot.get("generated_at"),
            "events_found": snapshot.get("events_found"),
            "coverage_pct": snapshot.get("coverage_pct"),
            "full_market_event_scan": snapshot.get("full_market_event_scan"),
        }
        st["event_risk"] = assess_event_risk(snapshot_events)

        # Do not silently replace an incomplete official chain with a
        # plan-restricted Fugle Snapshot endpoint.
        if len(working_rows) < 300:
            st["warnings"].append(
                "盤中有效報價不足 300 檔；本次不以 Fugle Snapshot 補洞，"
                "避免把方案權限或資料缺口誤判為完整市場。"
            )

        working_rows = apply_relative_strength(working_rows)

        passed = []
        for r in working_rows:
            ok, reasons = first_gate(r)
            r["gate_reasons"] = reasons
            if ok:
                r["rank_score"] = score_for_ranking(r)
                passed.append(r)

        passed.sort(key=lambda x: x["rank_score"], reverse=True)
        top = passed[:TOP_N]
        st["top100"] = top

        # Deep-dive enough rows to fill DEEP_DIVE_N verified, non-rejected
        # candidates. Confirmed limit-up / non-day-tradable names do not consume
        # the effective candidate quota.
        deep = []
        rejected = []
        unverified = []
        monitor_decisions = []
        paper_snapshots = []
        probe_limit = min(len(top), max(DEEP_DIVE_N * 4, DEEP_DIVE_N))

        for row in top[:probe_limit]:
            try:
                ks = get_candles(row["symbol"], "5")
                item = enrich(
                    row,
                    get_ticker(row["symbol"]),
                    get_quote(row["symbol"]),
                    ks,
                )
                item["classification_cap"] = (
                    "A"
                    if not st["full_market_scan"]
                    else "A+ eligible only after all gates"
                )

                x_flags = [f for f in item.get("flags", []) if str(f).startswith("X:")]
                if x_flags:
                    rejected.append(item)
                    continue

                features = build_features(
                    item,
                    ks.get("data", []) if isinstance(ks, dict) else [],
                    market_return_pct=None,
                ).to_dict()
                regime = detect_regime(
                    index_change_pct=None,
                    breadth_pct=None,
                    volatility_pct=features.get("volatility_5"),
                )
                preds = baseline_model_predictions(features, horizon_days=5)
                ml = ensemble(preds, regime.label)
                ml["models"] = [p.to_dict() for p in preds]
                ml["regime"] = regime.to_dict()
                ml["explainability"] = explain(features, ml)
                ml["validation"] = evaluate_validation_gate()
                item["features"] = features
                item["ml"] = ml
                item["market_intelligence"] = st["market_intelligence"]
                item["event_risk"] = st["event_risk"]
                item["structured_evidence_ledger"] = build_structured_evidence_ledger(
                    item, now.isoformat()
                )

                strategy_plan = build_breakout_plan(item, ks)
                item = apply_plan(item, strategy_plan)

                risk = evaluate_candidate(item, portfolio_context, policy)
                risk["status_zh"] = RISK_STATUS_ZH.get(risk["status"], risk["status"])
                risk["state_zh"] = RISK_STATE_ZH.get(risk["state"], risk["state"])
                item["risk"] = risk

                monitor = evaluate_monitor_state(
                    item,
                    previous_state=previous_monitor_state.get(
                        str(item.get("symbol") or "")
                    ),
                )
                item["monitor"] = monitor.to_dict()
                monitor_decisions.append(monitor)

                evidence_items = market_evidence_from_candidate(item, now.isoformat())
                evidence_ledger = build_knowledge_evidence_ledger(
                    evidence_items,
                    max_age_hours=1.0,
                    now=now,
                )
                item["evidence_ledger"] = evidence_ledger
                item["agent_orchestration"] = orchestrate(item, evidence_ledger)
                paper_snapshots.append(
                    build_paper_snapshot(
                        run_id=run_id,
                        observed_at=now.isoformat(),
                        item=item,
                        gate=paper_gate,
                    )
                )
                deep.append(item)
                if len(deep) >= DEEP_DIVE_N:
                    break

            except PermissionError as e:
                item = dict(row)
                item["flags"] = [f"Fugle深查權限不足:{e}"]
                item["classification_cap"] = "A"
                unverified.append(item)

            except Exception as e:
                item = dict(row)
                item["flags"] = [f"Fugle深查失敗:{type(e).__name__}"]
                item["classification_cap"] = "A"
                unverified.append(item)

        st["deep"] = deep
        st["deep_rejected"] = rejected[:20]
        st["deep_unverified"] = unverified[:20]
        st["monitor_engine"]["decisions"] = [
            d.to_dict() for d in monitor_decisions
        ]
        st["monitor_engine"]["transitions"] = [
            d.to_dict() for d in monitor_decisions if d.changed
        ]
        state_store.save(monitor_decisions)

        paper_path = OUT / "paper" / f"{run_id}.json"
        write_paper_run_file(paper_path, paper_snapshots)
        st["paper_trading"]["records"] = len(paper_snapshots)
        if PAPER_GCS_BUCKET:
            try:
                object_name = (
                    f"paper/{now:%Y/%m/%d}/{run_id}.json"
                )
                st["paper_trading"]["ledger_upload"] = upload_paper_run_to_gcs(
                    local_path=paper_path,
                    bucket_name=PAPER_GCS_BUCKET,
                    object_name=object_name,
                )
            except Exception as e:
                st["paper_trading"]["ledger_upload"] = {
                    "uploaded": False,
                    "reason": f"{type(e).__name__}: {e}",
                }
                st["warnings"].append(
                    "Paper Ledger 雲端備份失敗；本次仍保留本機輸出，"
                    "不影響交易決策 Gate。"
                )

        lines = [
            f"Sky Cloud Scanner v0.4｜{now:%Y-%m-%d %H:%M}",
            (
                f"官方母池 TWSE {ust['twse']}｜TPEx {ust['tpex']}｜"
                f"MIS有效報價 {len(rows)}｜第一層通過 {len(passed)}"
            ),
        ]

        if st["full_market_scan"]:
            lines.append("✅ 已完成嚴格定義的全市場資料鏈。")
        else:
            lines.append(
                "⚠ 未完成全市場掃描；任何候選最高只列 A，不得宣告 A+。"
            )

        lines.append(
            "來源：TWSE官方母池＋TPEx官方母池；盤中上市=TWSE MIS；"
            "上櫃 MIS 僅為操作備援，非 TPEx 官方完整盤中資料鏈。"
        )

        lines += [
            "",
            "【P0-M 市場情報 / P0-EVT 事件風險】",
            (
                f"市場偏向：{st['market_intelligence'].get('market_bias', 'UNKNOWN')}｜"
                f"上漲家數比：{st['market_intelligence'].get('breadth_pct')}%"
            ),
            (
                f"事件風險：{st['event_risk'].get('level', 'UNKNOWN')}｜"
                f"動作：{st['event_risk'].get('action', 'VERIFY_BEFORE_TRADE')}"
            ),
            "",
            "【P0-LAB Paper Trading】",
            (
                f"模式：{paper_gate.mode}｜"
                f"OOS：{paper_gate.oos_verdict}｜"
                f"模擬成交：{'允許' if paper_gate.simulation_allowed else '禁止'}｜"
                f"本輪紀錄：{len(paper_snapshots)}"
            ),
            "",
            "【P0-A 監控狀態】",
            (
                f"Backend：{state_store.backend}｜"
                f"Persistent：{state_store.persistent}"
            ),
            "",
            "【P0-X 執行成本 / P0-R 風控】",
            (
                f"成本Profile：{EXEC_COST_PROFILE}｜"
                f"執行成本模型："
                f"{'完整' if st['execution_engine']['cost_inputs_complete'] else 'Fee/Tax可用，Execution資料不足'}｜"
                f"Execution RR Gate：{'啟用' if EXEC_ENFORCE_GATE else '停用'}｜"
                f"最低 Execution RR：{EXEC_MIN_RR:.2f}"
            ),
            "",
            "【P0-R 風控總覽】",
            f"帳戶狀態：{RISK_STATE_ZH.get(portfolio_state, portfolio_state)}",
            (
                f"帳戶資金：{ACCOUNT_EQUITY:,.0f}｜"
                f"單筆風險上限：{RISK_PER_TRADE_PCT*100:.2f}%｜"
                f"單日最大虧損：{DAILY_LOSS_LIMIT_PCT*100:.2f}%｜"
                f"最大持倉風險：{MAX_PORTFOLIO_HEAT_PCT*100:.2f}%"
            ),
            "",
            "【可繼續深查候選】",
        ]
        if not deep:
            lines.append("目前沒有完成且通過基礎否決條件的深查候選；不產生交易建議。")

        for i, x in enumerate(deep[:10], 1):
            flags = "、".join(x.get("flags", [])) or "待確認"
            risk = x.get("risk", {})
            risk_status = risk.get("status_zh", "未檢查")
            risk_state = risk.get("state_zh", "未檢查")
            reasons = "、".join(risk.get("reasons", [])) or "無"
            required = "、".join(risk.get("required_inputs", []))
            risk_line = (
                f"風控：{risk_status}｜帳戶狀態：{risk_state}｜"
                f"建議部位：{risk.get('recommended_shares', 0):,}股"
            )
            if required:
                risk_line += f"｜缺少：{required}"
            lines.append(
                f'{i}. {x["symbol"]} {x.get("name","")} '
                f'{x["last"]:.2f} ({x["change_pct"]:+.2f}%) '
                f'量{x.get("volume",0):,}｜{flags}｜上限:{x.get("classification_cap")}'
            )
            lines.append(f"   {risk_line}")
            plan = x.get("strategy_plan")
            if plan:
                lines.append(
                    f'   P0-S：{plan.get("setup")}｜'
                    f'Trigger {plan.get("trigger")}｜'
                    f'最高接受 {plan.get("max_entry")}｜'
                    f'Stop {plan.get("stop")}｜'
                    f'Target {plan.get("target")}｜'
                    f'RR {plan.get("rr")}｜研究用'
                )
            monitor = x.get("monitor") or {}
            if monitor:
                lines.append(
                    f'   P0-A：{monitor.get("state_zh", monitor.get("state"))}｜'
                    f'動作：{monitor.get("action")}｜{monitor.get("reason")}'
                )
            ml = x.get("ml", {})
            if ml:
                consensus_zh = {
                    "BULLISH": "偏多",
                    "BEARISH": "偏空",
                    "NEUTRAL": "中性",
                }.get(ml.get("consensus"), ml.get("consensus", "未判定"))
                lines.append(
                    f"   ML研究層：{consensus_zh}｜"
                    f"5日預期報酬：{ml.get('expected_return_pct')}%｜"
                    f"信心：{float(ml.get('confidence') or 0)*100:.1f}%｜"
                    f"市場狀態：{ml.get('regime', {}).get('label', '未判定')}｜"
                    f"資格：研究用"
                )
            orchestration = x.get("agent_orchestration", {})
            ledger = x.get("evidence_ledger", {})
            if orchestration:
                lines.append(
                    f"   P0-K/P0-AG：證據{ledger.get('evidence_count', 0)}筆｜"
                    f"衝突:{'是' if ledger.get('conflict') else '否'}｜"
                    f"代理決策狀態:{orchestration.get('decision_status', '未判定')}"
                )
            if reasons != "無":
                lines.append(f"   原因：{reasons}")

        transitions = st["monitor_engine"]["transitions"]
        lines += ["", "【P0-A 盤中警戒】"]
        if not monitor_decisions:
            lines.append("本次沒有可監控的深查候選。")
        elif not transitions:
            lines.append("本次無狀態變化；延續前次監控狀態。")
        else:
            for d in transitions[:10]:
                prev = d.get("previous_state") or "首次"
                lines.append(
                    f'{d["symbol"]}｜{prev} → '
                    f'{d.get("state_zh", d["state"])}｜'
                    f'動作：{d["action"]}｜{d["reason"]}'
                )

        if rejected:
            lines += ["", "【已確認淘汰，不占有效深查名額】"]
            for x in rejected[:8]:
                flags = "、".join(x.get("flags", []))
                lines.append(
                    f'{x["symbol"]} {x.get("name","")}｜{flags}'
                )

        if unverified:
            lines += ["", "【資料不足／深查未完成】"]
            for x in unverified[:8]:
                flags = "、".join(x.get("flags", []))
                lines.append(
                    f'{x["symbol"]} {x.get("name","")}｜{flags}'
                )

        lines += [
            "",
            "注意：rank_score 與 relative_strength_score 僅用於候選排序／橫向比較，不是勝率、SSS 或 EES。",
            "P0-R 規則：任何 AI／策略訊號都不得繞過風控；缺少停損、目標價或帳戶資金時，風控一律標示「資料不足」，不得視為可進場。",
            "P0-K 規則：任何重要結論必須可追溯；過期、衝突或無來源資訊不得升級為主要交易依據。",
            "P0-AG 規則：任何單一 Agent 均不得直接產生可執行交易；必須再通過 P0-C 與 P0-R。",
            "P0-ML 規則：目前僅為研究用 baseline；未通過 Walk-forward／OOS／成本壓力／資料洩漏檢查／Paper Trading 前，不得提升為正式交易依據。",
            "Paper Trading 規則：shadow 僅留痕；paper 仍須 OOS=PASS_TO_PAPER_TRADING 才可模擬成交，任何模式都不得送真實委託。",
            (
                "A+ 必須再通過 Market Gate→Sector/RS→MTF→SSS→Phase→"
                "Anti-Chase→Breakout Quality→Setup+Trigger→"
                "Devil’s Advocate→EES→RR Gate。"
            ),
        ]

        msg = "\n".join(lines)
        (OUT / "latest.txt").write_text(msg, encoding="utf-8")
        (OUT / "latest.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        send_telegram(msg)

    except Exception as e:
        err = (
            f"Sky Cloud Scanner v0.4 執行失敗｜{now:%Y-%m-%d %H:%M}\n"
            f"{type(e).__name__}: {e}\n不產生交易建議。"
        )
        st["warnings"].append(err)
        (OUT / "latest.txt").write_text(err, encoding="utf-8")
        (OUT / "latest.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(err)
        raise

if __name__ == "__main__":
    run()
