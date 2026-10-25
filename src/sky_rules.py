from .ranking_engine import screening_rank_score
from .config import MAX_PRICE, MIN_VOLUME, MIN_TRADE_VALUE

def spread_pct(row):
    bid=row.get("bid"); ask=row.get("ask")
    if not bid or not ask or ask < bid: return None
    mid=(bid+ask)/2
    return (ask-bid)/mid*100 if mid else None

def first_gate(row):
    reasons=[]
    if row.get("last") is None or row["last"]>MAX_PRICE: reasons.append(f"股價>{MAX_PRICE:g}或無有效成交價")
    if row.get("volume",0)<MIN_VOLUME: reasons.append(f"量<{MIN_VOLUME}張")
    if row.get("trade_value",0)<MIN_TRADE_VALUE: reasons.append(f"成交值<{MIN_TRADE_VALUE:,.0f}")
    sp=spread_pct(row)
    if sp is not None and sp>0.8: reasons.append(f"價差過大({sp:.2f}%)")
    return not reasons,reasons

# Legacy compatibility alias. Canonical ranking lives in P0-O / ranking_engine.py.
score_for_ranking = screening_rank_score

def enrich(row,ticker,quote,candles):
    o=dict(row)
    o["can_day_trade"]=bool(ticker.get("canDayTrade")); o["can_buy_day_trade"]=bool(ticker.get("canBuyDayTrade"))
    o["limit_up"]=ticker.get("limitUpPrice"); o["industry"]=ticker.get("industry")
    o["avg_price"]=quote.get("avgPrice"); o["fugle_close"]=quote.get("closePrice")
    o["fugle_high"]=quote.get("highPrice"); o["fugle_low"]=quote.get("lowPrice")
    o["fugle_volume"]=quote.get("total",{}).get("tradeVolume") if isinstance(quote.get("total"),dict) else None
    o["is_limit_up"]=bool(o.get("limit_up") is not None and o.get("fugle_close") is not None and float(o["fugle_close"])>=float(o["limit_up"]))
    ks=candles.get("data",[]) if isinstance(candles,dict) else []
    o["k_count"]=len(ks)
    if len(ks)>=2:
        o["last_k_close"]=ks[-1].get("close"); o["prev_k_close"]=ks[-2].get("close")
        o["last_k_volume"]=ks[-1].get("volume"); o["prev_k_volume"]=ks[-2].get("volume")
    flags=[]
    if o["is_limit_up"]: flags.append("X:漲停")
    if not o["can_day_trade"]: flags.append("X:不可當沖")
    if o.get("avg_price") and o.get("fugle_close"): flags.append("站上均價" if o["fugle_close"]>=o["avg_price"] else "低於均價")
    if o.get("last_k_volume") and o.get("prev_k_volume") and o["last_k_volume"]>o["prev_k_volume"]*1.5: flags.append("5分K量增")
    o["flags"]=flags
    return o
