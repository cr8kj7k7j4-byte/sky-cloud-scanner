from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
DATA_QUALITY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class DataQualityPolicy:
    max_quote_age_seconds: int = 90
    require_volume: bool = True
    require_high_low: bool = False
    require_bid_ask: bool = False

    def to_dict(self):
        return asdict(self)


def _parse_quote_time(value, now):
    if not value:
        return None
    text = str(value).strip()
    try:
        if "T" in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.astimezone(TZ) if dt.tzinfo else dt.replace(tzinfo=TZ)
        parts = text.split(":")
        if len(parts) >= 2:
            hh, mm = int(parts[0]), int(parts[1])
            ss = int(float(parts[2])) if len(parts) >= 3 else 0
            dt = now.replace(hour=hh, minute=mm, second=ss, microsecond=0)
            # Handles just-after-midnight diagnostics without turning a previous-day
            # quote into a future timestamp.
            if dt - now > timedelta(hours=12):
                dt -= timedelta(days=1)
            return dt
    except Exception:
        return None
    return None


def validate_quote(row, now=None, policy=None):
    row = row or {}
    policy = policy or DataQualityPolicy()
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    else:
        now = now.astimezone(TZ)

    reasons = []
    warnings = []

    symbol = str(row.get("symbol") or "").strip()
    last = row.get("last")
    volume = row.get("volume")
    high = row.get("high")
    low = row.get("low")
    bid = row.get("bid")
    ask = row.get("ask")
    quote_time = row.get("quote_time") or row.get("data_time") or row.get("timestamp")

    if not symbol:
        reasons.append("缺少股票代碼")
    try:
        if last is None or float(last) <= 0:
            reasons.append("缺少有效現價")
    except Exception:
        reasons.append("現價格式錯誤")

    if policy.require_volume:
        try:
            if volume is None or float(volume) < 0:
                reasons.append("缺少有效成交量")
        except Exception:
            reasons.append("成交量格式錯誤")

    if policy.require_high_low and (high is None or low is None):
        reasons.append("缺少當日高低價")

    if policy.require_bid_ask and (bid is None or ask is None):
        reasons.append("缺少買賣報價")

    quote_dt = _parse_quote_time(quote_time, now)
    age_seconds = None
    if quote_dt is None:
        reasons.append("缺少或無法解析報價時間")
    else:
        age_seconds = max(0.0, (now - quote_dt).total_seconds())
        if age_seconds > policy.max_quote_age_seconds:
            reasons.append(f"報價逾時>{policy.max_quote_age_seconds}秒")
        if quote_dt > now + timedelta(seconds=5):
            warnings.append("報價時間晚於系統時間")

    if bid is not None and ask is not None:
        try:
            if float(bid) > float(ask):
                warnings.append("買價高於賣價，需檢查來源")
        except Exception:
            warnings.append("買賣報價格式異常")

    ok = not reasons
    return {
        "schema_version": DATA_QUALITY_SCHEMA_VERSION,
        "ok": ok,
        "status": "PASS" if ok else "BLOCK",
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "reasons": reasons,
        "warnings": warnings,
        "source": row.get("quote_source"),
    }


def validate_market_rows(rows, now=None, policy=None):
    policy = policy or DataQualityPolicy()
    checked = []
    pass_count = 0
    for row in rows or []:
        result = validate_quote(row, now=now, policy=policy)
        checked.append(result)
        pass_count += int(result["ok"])
    total = len(checked)
    return {
        "schema_version": DATA_QUALITY_SCHEMA_VERSION,
        "total": total,
        "pass_count": pass_count,
        "block_count": total - pass_count,
        "pass_rate": round(pass_count / total, 4) if total else 0.0,
        "policy": policy.to_dict(),
    }
