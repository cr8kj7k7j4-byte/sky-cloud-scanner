import os

def _b(name, default="0"):
    return os.getenv(name, default).strip().lower() in {"1","true","yes","on"}

FUGLE_API_KEY = os.getenv("FUGLE_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
MAX_PRICE = float(os.getenv("MAX_PRICE", "100"))
TOP_N = int(os.getenv("TOP_N", "100"))
DEEP_DIVE_N = int(os.getenv("DEEP_DIVE_N", "12"))
MIN_VOLUME = int(os.getenv("MIN_VOLUME", "500"))
MIN_TRADE_VALUE = float(os.getenv("MIN_TRADE_VALUE", "10000000"))
STRICT_OFFICIAL_MODE = _b("STRICT_OFFICIAL_MODE", "1")
ALLOW_MIS_OTC_FALLBACK = _b("ALLOW_MIS_OTC_FALLBACK", "1")
