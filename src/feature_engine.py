from dataclasses import dataclass, asdict
from statistics import mean, pstdev


@dataclass(frozen=True)
class FeatureSnapshot:
    momentum_1: float | None
    momentum_5: float | None
    volume_ratio: float | None
    vwap_distance_pct: float | None
    intraday_range_pct: float | None
    volatility_5: float | None
    relative_strength: float | None

    def to_dict(self):
        return asdict(self)


def _safe_pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (float(a) / float(b) - 1.0) * 100.0


def build_features(candidate, candles=None, market_return_pct=None):
    candidate = candidate or {}
    candles = candles or []
    closes = [float(x["close"]) for x in candles if x.get("close") is not None]
    volumes = [float(x["volume"]) for x in candles if x.get("volume") is not None]

    last = candidate.get("fugle_close", candidate.get("last"))
    avg_price = candidate.get("avg_price")
    high = candidate.get("fugle_high")
    low = candidate.get("fugle_low")

    momentum_1 = None
    momentum_5 = None
    volatility_5 = None
    if len(closes) >= 2:
        momentum_1 = _safe_pct(closes[-1], closes[-2])
    if len(closes) >= 6:
        momentum_5 = _safe_pct(closes[-1], closes[-6])
        rets = []
        for i in range(len(closes) - 5, len(closes)):
            prev = closes[i - 1]
            if prev:
                rets.append(closes[i] / prev - 1.0)
        if rets:
            volatility_5 = pstdev(rets) * 100.0

    volume_ratio = None
    if len(volumes) >= 2:
        base = mean(volumes[:-1]) if volumes[:-1] else 0
        if base > 0:
            volume_ratio = volumes[-1] / base

    vwap_distance_pct = _safe_pct(last, avg_price)

    intraday_range_pct = None
    if high is not None and low is not None and last not in (None, 0):
        intraday_range_pct = (float(high) - float(low)) / float(last) * 100.0

    relative_strength = None
    cp = candidate.get("change_pct")
    if cp is not None and market_return_pct is not None:
        relative_strength = float(cp) - float(market_return_pct)

    return FeatureSnapshot(
        momentum_1=momentum_1,
        momentum_5=momentum_5,
        volume_ratio=volume_ratio,
        vwap_distance_pct=vwap_distance_pct,
        intraday_range_pct=intraday_range_pct,
        volatility_5=volatility_5,
        relative_strength=relative_strength,
    )


def _best_level(levels):
    if not isinstance(levels, list) or not levels:
        return None, None
    first = levels[0] if isinstance(levels[0], dict) else {}
    return first.get("price"), first.get("size")


def enrich_candidate_context(row, ticker, quote, candles):
    """Canonical P0-F/Data enrichment for deep-dive candidate context."""
    o = dict(row or {})
    ticker = ticker or {}
    quote = quote or {}
    candles = candles or {}

    o["can_day_trade"] = bool(ticker.get("canDayTrade"))
    o["can_buy_day_trade"] = bool(ticker.get("canBuyDayTrade"))
    o["limit_up"] = ticker.get("limitUpPrice")
    o["industry"] = ticker.get("industry")
    o["avg_price"] = quote.get("avgPrice")
    o["fugle_close"] = quote.get("closePrice")
    o["fugle_high"] = quote.get("highPrice")
    o["fugle_low"] = quote.get("lowPrice")

    total = quote.get("total")
    o["fugle_volume"] = total.get("tradeVolume") if isinstance(total, dict) else None

    # W6 forward L1 evidence. Preserve source fields without interpreting a
    # midpoint or trigger price as executable. Fugle intraday quote exposes
    # best-five bid/ask arrays plus lastUpdated/serial; only level 1 is kept
    # here for forward execution research.
    bid, bid_size = _best_level(quote.get("bids"))
    ask, ask_size = _best_level(quote.get("asks"))
    o["l1_bid"] = bid
    o["l1_ask"] = ask
    o["l1_bid_size"] = bid_size
    o["l1_ask_size"] = ask_size
    o["l1_quote_time"] = quote.get("lastUpdated")
    o["l1_quote_serial"] = quote.get("serial")
    o["l1_quote_source"] = "FUGLE_INTRADAY_QUOTE"

    o["is_limit_up"] = bool(
        o.get("limit_up") is not None
        and o.get("fugle_close") is not None
        and float(o["fugle_close"]) >= float(o["limit_up"])
    )

    ks = candles.get("data", []) if isinstance(candles, dict) else []
    o["k_count"] = len(ks)
    if len(ks) >= 2:
        o["last_k_close"] = ks[-1].get("close")
        o["prev_k_close"] = ks[-2].get("close")
        o["last_k_volume"] = ks[-1].get("volume")
        o["prev_k_volume"] = ks[-2].get("volume")

    flags = []
    if o["is_limit_up"]:
        flags.append("X:漲停")
    if not o["can_day_trade"]:
        flags.append("X:不可當沖")
    if o.get("avg_price") and o.get("fugle_close"):
        flags.append("站上均價" if o["fugle_close"] >= o["avg_price"] else "低於均價")
    if (
        o.get("last_k_volume")
        and o.get("prev_k_volume")
        and o["last_k_volume"] > o["prev_k_volume"] * 1.5
    ):
        flags.append("5分K量增")
    o["flags"] = flags
    return o
