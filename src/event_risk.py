HIGH_RISK_TYPES = {
    "FED", "CPI", "WAR", "GEOPOLITICAL", "EARNINGS",
    "MSCI", "DISPOSITION", "ATTENTION", "EX_DIVIDEND",
}


def assess_event_risk(events=None):
    events = events or []
    active = [e for e in events if e.get("active", True)]
    high = [e for e in active if str(e.get("type", "")).upper() in HIGH_RISK_TYPES]

    if not active:
        return {
            "level": "UNKNOWN",
            "action": "VERIFY_BEFORE_TRADE",
            "events": [],
            "note": "尚未串接即時事件來源，不得假設無事件風險",
        }

    if high:
        return {
            "level": "HIGH",
            "action": "REDUCE_OR_BLOCK",
            "events": high,
            "note": "高事件風險僅為風控閘門，不代表方向",
        }

    return {
        "level": "NORMAL",
        "action": "STANDARD_RISK",
        "events": active,
        "note": "仍須搭配市場、族群與交易 Trigger",
    }
