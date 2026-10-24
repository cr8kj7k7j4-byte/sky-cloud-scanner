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

# P0-R Risk & Portfolio Engine
ACCOUNT_EQUITY = float(os.getenv("ACCOUNT_EQUITY", "0"))
RISK_PER_TRADE_PCT = float(os.getenv("RISK_PER_TRADE_PCT", "0.005"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "0.015"))
MAX_PORTFOLIO_HEAT_PCT = float(os.getenv("MAX_PORTFOLIO_HEAT_PCT", "0.03"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.20"))
CORRELATION_LIMIT_PCT = float(os.getenv("CORRELATION_LIMIT_PCT", "0.02"))
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", "3"))
CAUTION_LOSS_STREAK = int(os.getenv("CAUTION_LOSS_STREAK", "3"))
DEFENSIVE_LOSS_STREAK = int(os.getenv("DEFENSIVE_LOSS_STREAK", "5"))
LOCKDOWN_DRAWDOWN_PCT = float(os.getenv("LOCKDOWN_DRAWDOWN_PCT", "0.06"))
LOT_SIZE = int(os.getenv("LOT_SIZE", "1000"))
DAILY_PNL = float(os.getenv("DAILY_PNL", "0"))
OPEN_RISK = float(os.getenv("OPEN_RISK", "0"))
CONCURRENT_POSITIONS = int(os.getenv("CONCURRENT_POSITIONS", "0"))
CORRELATED_OPEN_RISK = float(os.getenv("CORRELATED_OPEN_RISK", "0"))
ACCOUNT_DRAWDOWN_PCT = float(os.getenv("ACCOUNT_DRAWDOWN_PCT", "0"))
CONSECUTIVE_LOSSES = int(os.getenv("CONSECUTIVE_LOSSES", "0"))

# P0-A Alert & Monitoring state store
MONITOR_STATE_BACKEND = os.getenv("MONITOR_STATE_BACKEND", "file").strip().lower()
REDIS_URL = os.getenv("REDIS_URL", "").strip()
MONITOR_STATE_REDIS_KEY = os.getenv("MONITOR_STATE_REDIS_KEY", "sky:p0a:monitor_state").strip()

# P0-EVT Premarket Event Intelligence
PREMARKET_REDIS_KEY = os.getenv("PREMARKET_REDIS_KEY", "sky:p0evt:latest").strip()
