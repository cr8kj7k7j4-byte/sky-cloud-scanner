from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class CommandRoute:
    command_family: str
    data_mode: str
    realtime_required: bool
    whole_market_required: bool
    symbol_required: bool
    execution_target: str
    notes: str

    def to_dict(self):
        return asdict(self)


# W0 #363: 2026-11-25 verified close <= 100 TWD; user-directed removal
# of nine >100 TWD symbols from the previous 21-symbol research watchlist.
# Historical evidence remains in GitHub. No live runner or automatic trading.
# Future trade eligibility STILL requires freshly verified <=100 TWD price.
SKY_MARGIN_WATCHLIST = (
    "2337", "6217", "3362", "8045", "8043", "2233",
    "5464", "4764", "1587", "3447", "2230", "6994",
)
SKY_MARGIN_PRESENTATION = "SKY_MOBILE_TABLE_V1_0"


def watchlist_for_command(command: str) -> tuple[str, ...] | None:
    """Explicit candidate universe; never implies verified data or dispatch."""
    normalized = " ".join((command or "").strip().split())
    if re.fullmatch(r"Sky\s*維持率", normalized, re.I):
        return SKY_MARGIN_WATCHLIST
    return None


# W0 #363: Conversation aliases are classified here, not GitHub dispatch hooks.
# Never imply that a matching name has passed live E2E or that a new
# margin-maintenance data provider/runner is authorized.
_SHORTCUT_PATTERNS = [
    (
        re.compile(r"^Sky\s*維持率$", re.I),
        CommandRoute(
            "SKY_MARGIN_MAINTENANCE_RESEARCH", "RESEARCH_ONLY_SOURCE_UNVERIFIED",
            False, False, False, "HOLD_PROVIDER_AND_SOURCE_CONFIRMATION",
            "User-defined 12-symbol <=100 TWD (2026-11-25 close) list only;  "
            "Candidate research only: financing maintenance ratio below 120%, "
            "foreign/investment-trust net buying over 50 lots, price <=100 TWD, "
            "capital <=3 billion TWD and volume >=100 lots except limit-down. "
            "Requires independently verified ratio, institutional flows, volume, "
            "universe/date, and authorized Fugle price confirmation. No live "
            "GitHub command runner or buy eligibility has been certified."
        ),
    ),
    (
        re.compile(r"^Sky\s*當沖$", re.I),
        CommandRoute(
            "SKY_DAYTRADE_SCAN", "WHOLE_MARKET_REALTIME", True, True, False,
            "src.main (existing scanner; trigger not implied)",
            "Conversation alias only. Enforce A1/A2, actual executed-trade "
            "timestamps and P0-R; E2E not yet certified."
        ),
    ),
    (
        re.compile(r"^Sky\s*波段$", re.I),
        CommandRoute(
            "SKY_SWING_V10_LIVE_OBSERVATION",
            "WHOLE_MARKET_REALTIME_RESEARCH_ONLY", True, True, False,
            ".github/workflows/swing-live-scan.yml --mode swing (existing observation)",
            "Conversation alias only. Swing V1.0 rule executable remains BLOCKED; "
            "Swing V1.1 is Research; no verified entry authorization."
        ),
    ),
    (
        re.compile(r"^Sky\s*盤中掃描$", re.I),
        CommandRoute(
            "SKY_DAYTRADE_SCAN", "WHOLE_MARKET_REALTIME", True, True, False,
            ".github/workflows/scan.yml (existing governed scanner)",
            "Conversation alias only; schedule/dispatch and live evidence "
            "require independent verification. No automatic orders."
        ),
    ),
    (
        re.compile(r"^Sky\s*盤後分析$", re.I),
        CommandRoute(
            "SKY_POSTMARKET_RESEARCH", "POSTMARKET_OBSERVATION_ONLY",
            False, True, False,
            ".github/workflows/scan.yml --mode postmarket_observation",
            "Requires verified official close/date, authorized source coverage "
            "and same-run Artifact; no intraday trade timestamp or buy signal."
        ),
    ),
    (
        re.compile(r"^Sky\s*系統狀態$", re.I),
        CommandRoute(
            "SKY_UNIFIED_SYSTEM_HEALTH", "OPERATIONAL_EVIDENCE",
            False, False, False,
            "sky-unified-commands.yml: system_health (existing mode)",
            "Conversation alias only. Read actual Run/SHA/Artifact; unknown "
            "checks stay UNKNOWN. This is not an Actions trigger."
        ),
    ),
    (
        re.compile(r"^Sky\s*工程修復$", re.I),
        CommandRoute(
            "SKY_W0_ENGINEERING_REVIEW", "W0_GOVERNED_REPAIR",
            False, False, False, "GitHub issue #363 W0 only",
            "Conversation request, NOT a GitHub workflow command. W0 must "
            "recheck current main, PRs and ownership before any writes."
        ),
    ),
    (
        re.compile(r"^Sky\s*正式驗收$", re.I),
        CommandRoute(
            "SKY_SEVEN_LAYER_ACCEPTANCE", "EVIDENCE_REVIEW_ONLY",
            False, False, False, "GitHub issue #363 W4 evidence / W0 decision",
            "Conversation alias only. Verify seven gates separately; "
            "CI PASS is not live E2E, strategy validation or Production approval."
        ),
    ),
]


_PATTERNS = [
    (
        re.compile(r"^Sky\s*(?:全市場即時行情|全市場即時行情檢查)$", re.I),
        CommandRoute(
            "SKY_WHOLE_MARKET_LIVE_DATA_AUDIT", "WHOLE_MARKET_REALTIME",
            True, True, False, "sky-unified-commands.yml: all_market",
            "Require verified current-session executed trades across TWSE/TPEx. "
            "Daily cross-sections and shortlisted live quotes are not full-market live."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:當沖空方研究|空方研究)(?:\s*掃一下|\s*現在掃一次)?$", re.I),
        CommandRoute(
            "SKY_SHORT_RESEARCH", "WHOLE_MARKET_REALTIME_RESEARCH_BLOCKED",
            True, True, False, "W2 short research; standalone realtime runner not verified",
            "Research only; requires independent short structures, short eligibility, "
            "full-market quotes, causal evidence and W6 cost gate. No short signal."
        ),
    ),
    (
        re.compile(r"^Sky\s*v1\.4\s*Dynamic\s*Capital\s*Rotation\s*掃一下$", re.I),
        CommandRoute(
            "SKY_DAYTRADE_SCAN", "WHOLE_MARKET_REALTIME",
            True, True, False, "src.main",
            "Alias to Sky 當沖現在掃一次, with strict missing-market-data rejection."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:全市場完整掃描|六模型全市場即時掃描|查詢六模型研究訊號)$", re.I),
        CommandRoute(
            "SKY_SIX_MODEL_RESEARCH_VISIBILITY",
            "WHOLE_MARKET_LIVE_RESEARCH_WITH_EXPLICIT_MODEL_VERIFICATION",
            True, True, False,
            "scan.yml + output/research_visibility/latest.json + W2 model registry",
            "Return real observed market evidence even when Production denies entry; "
            "six-model actual inference requires six verified runners, not three research rules. "
            "No fabricated scores, prices, probability or trade authorization."
        ),
    ),
    (
        re.compile(r"^Sky\s*全市場掃描$", re.I),
        CommandRoute(
            "SKY_UNIFIED_MARKET_SCAN", "MULTI_MODEL_MARKET", True, True, False,
            "sky-unified-commands.yml: all_market",
            "Composite candidate report: intraday production baseline; swing and 5D research only; short research cannot imply authorization. No automatic orders."
        ),
    ),
    (
        re.compile(r"^Sky\s*系統健康檢查$", re.I),
        CommandRoute(
            "SKY_UNIFIED_SYSTEM_HEALTH", "OPERATIONAL_EVIDENCE", False, False, False,
            "sky-unified-commands.yml: system_health",
            "Inspect data-source diagnostics, workflow health and artifacts; unknown checks must be shown as UNKNOWN."
        ),
    ),
    (
        re.compile(r"^Sky\s*全模型驗證$", re.I),
        CommandRoute(
            "SKY_UNIFIED_MODEL_VALIDATION", "GOVERNED_RESEARCH_EVIDENCE", False, False, False,
            "sky-unified-commands.yml: model_validation",
            "Read governing registries and test evidence; no promotion or synthetic backtest."
        ),
    ),
    (
        re.compile(r"^Sky\s*快掃(?:更新)?$", re.I),
        CommandRoute(
            "SKY_QUICK_SCAN", "WHOLE_MARKET_REALTIME", True, True, False,
            "src.main",
            "TWSE+TPEx official universe; TWSE MIS TSE+OTC operational quotes; Fugle deep-dive."
        ),
    ),
    (
        re.compile(r"^Sky\s*當沖(?:現在掃一次|快掃)$", re.I),
        CommandRoute(
            "SKY_DAYTRADE_SCAN", "WHOLE_MARKET_REALTIME", True, True, False,
            "src.main",
            "Canonical intraday whole-market scanner."
        ),
    ),
    (
        re.compile(r"^Sky\s*Swing\s*5D\s*(?:快掃|現在掃一次)?$", re.I),
        CommandRoute(
            "SKY_SWING_5D", "WHOLE_MARKET_REALTIME", True, True, False,
            "src.swing_live_scanner --mode swing5d",
            "Research-only/HOLD candidate generation; realtime availability does not imply promotion."
        ),
    ),
    (
        re.compile(r"^Sky\s*波段現在掃一次$", re.I),
        CommandRoute(
            "SKY_SWING_V10_LIVE_OBSERVATION", "WHOLE_MARKET_REALTIME_RESEARCH_ONLY", True, True, False,
            ".github/workflows/swing-live-scan.yml --mode swing",
            "Use the existing governed Swing observation runner only. Sky Swing V1.0 remains the unchanged Production baseline, but its exact executable rule specification is BLOCKED; this runner is observation/candidate evidence only, not a V1.0 signal. Swing V1.1 remains Research only. No buy authorization or automatic orders."
        ),
    ),
    (
        re.compile(r"^Sky\s*波段快掃$", re.I),
        CommandRoute(
            "SKY_SWING_SCAN", "WHOLE_MARKET_REALTIME", True, True, False,
            "src.swing_live_scanner --mode swing",
            "Broad swing candidate generation only; not an executable V1.1 entry decision."
        ),
    ),
    (
        re.compile(r"^Sky\s*Swing\s*V1\.1\s*[｜|]?\s*現在掃一次$", re.I),
        CommandRoute(
            "SKY_SWING_V11_LIVE", "WHOLE_MARKET_REALTIME_PLUS_CANONICAL_DAILY", True, True, False,
            "src.swing_v11_live_scanner",
            "Frozen D-close signal + D+1 open semantics preserved; current price never rewrites entry."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:當沖更新|波段更新|Swing\s*5D\s*更新|完整分析)\s+\d{4,6}$", re.I),
        CommandRoute(
            "SKY_SINGLE_STOCK_UPDATE", "SINGLE_STOCK_REALTIME", True, False, True,
            "Fugle connector realtime quote + relevant market context",
            "MANDATORY: fetch Fugle realtime quote first; stale public web data must never substitute for current price."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:當沖持倉更新|波段持倉更新|持倉更新)\s+\d{4,6}.*$", re.I),
        CommandRoute(
            "SKY_POSITION_UPDATE", "SINGLE_STOCK_REALTIME", True, False, True,
            "Fugle single-stock realtime quote + PMS/P0-R",
            "Position management must use latest obtainable quote and timestamp."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:警戒|即時警戒|全市場警戒)(?:\s*現在掃一次)?$", re.I),
        CommandRoute(
            "SKY_ALERT_WHOLE_MARKET_OBSERVATION",
            "WHOLE_MARKET_REALTIME_OBSERVATION", True, True, False,
            "research.sky_alert_reader --input output/sky_quickscan_information/full_universe.json (read-only; no scan)",
            "Read-only information-first full TWSE+TPEx universe report, including "
            "unverified or missing quote labels; trade eligibility remains blocked "
            "until independent production gates pass. No automatic orders."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:持倉|持倉監控)$", re.I),
        CommandRoute(
            "SKY_MONITOR", "WATCHLIST_OR_POSITION_REALTIME", True, False, False,
            "P0-A/PMS realtime refresh",
            "Refresh monitored candidates/positions with latest quotes before status output."
        ),
    ),
    (
        re.compile(r"^Sky\s*盤後複盤\s*[｜|]?\s*波段$", re.I),
        CommandRoute(
            "SKY_SWING_POSTMARKET_REVIEW",
            "POSTMARKET_DAILY_AND_SIGNAL_LEDGER", False, True, False,
            "swing-postmarket-research.yml + historical signal/outcome ledger",
            "Run only after verified official D-close. Existing workflow is research "
            "observations, NOT a verified trade-level review. Missing signal, fills, "
            "costs and outcomes must stay UNKNOWN. Preserve freshness and P0-R gates."
        ),
    ),
    (
        re.compile(r"^Sky\s*(?:回測目前模型|回測.*|驗證.*)$", re.I),
        CommandRoute(
            "SKY_RESEARCH_VALIDATION", "HISTORICAL_PIT", False, False, False,
            "W1/W2/W3A historical validation pipelines",
            "Backtest/validation commands must remain historical PIT; do not replace with realtime data."
        ),
    ),
]


def route_command(command: str) -> CommandRoute:
    normalized = " ".join((command or "").strip().split())

    # W0 #363 minimal mobile commands: classify only, never assert live success.
    if re.fullmatch(r"Sky\s*分析\s+\d{4,6}", normalized, re.I):
        return CommandRoute(
            "SKY_SINGLE_STOCK_UPDATE", "SINGLE_STOCK_REALTIME",
            True, False, True,
            "Fugle connector realtime quote + P0-R (verification required)",
            "A1 observation cannot certify an A2 execution. Missing certified quote, "
            "timestamp, trigger or cost-adjusted risk evidence stays HOLD/NO_TRADE."
        )
    if re.fullmatch(r"Sky\s*持股檢查(?:\s+.*)?", normalized, re.I):
        return CommandRoute(
            "SKY_POSITION_REVIEW", "USER_POSITION_EVIDENCE_REQUIRED",
            False, False, False,
            "HOLD_USER_POSITION_EVIDENCE",
            "No broker positions are connected or presumed. Require user-provided "
            "actual symbol, quantity, cost, stop and realized P&L before risk review; "
            "verify Fugle quote separately; never place orders."
        )
    for pattern, route in _SHORTCUT_PATTERNS + _PATTERNS:
        if pattern.match(normalized):
            return route

    # Natural-language single-stock questions must route through Fugle, too.
    # Example: "1569 濱川 當沖要怎麼操作，請給我多空評分與停損".
    if re.match(r"^\d{4,6}(?:\s+|$)", normalized) and any(
        token in normalized for token in ("當沖", "即時", "買進", "停損", "多空", "最高接受價")
    ):
        return CommandRoute(
            "SKY_SINGLE_STOCK_UPDATE", "SINGLE_STOCK_REALTIME",
            True, False, True,
            "Fugle connector realtime quote; cloud: sky-single-stock-realtime.yml",
            "MANDATORY: refresh trade price, local trade timestamp, quote eligibility; "
            "stale public web data must never substitute for a current quote; "
            "missing intraday-bar or verified trigger data must not produce scores/entry/stop."
        )

    # Fail closed: any unrecognized Sky command that sounds current must request
    # a fresh quote instead of silently falling back to stale public web data.
    if normalized.lower().startswith("sky"):
        realtime_hint = any(
            token in normalized
            for token in ("現在", "更新", "快掃", "持倉", "警戒", "完整分析", "掃一次")
        )
        return CommandRoute(
            "SKY_UNRECOGNIZED",
            "REALTIME_REQUIRED_UNROUTED" if realtime_hint else "UNROUTED",
            realtime_hint,
            False,
            False,
            "ROUTER_REVIEW_REQUIRED",
            "Unknown Sky command must not silently use stale data; add an explicit route before execution."
        )

    return CommandRoute(
        "NON_SKY", "UNROUTED", False, False, False, "NONE",
        "Not a Sky command."
    )


UPDATE_PRESENTATION = "SKY_MOBILE_TABLE_V1_0"


def presentation_for_command(command: str) -> str | None:
    """Canonical presentation for Sky commands.

    Every Sky command containing 更新 uses the same 10-column mobile decision
    table. Position updates may append position/P&L details after the table.
    """
    normalized = " ".join((command or "").strip().split())
    if watchlist_for_command(normalized) is not None:
        return SKY_MARGIN_PRESENTATION
    if normalized.lower().startswith("sky") and "更新" in normalized:
        return UPDATE_PRESENTATION
    return None
