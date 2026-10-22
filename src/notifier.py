import requests
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(text); return False
    r=requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",json={"chat_id":TELEGRAM_CHAT_ID,"text":text[:4000],"disable_web_page_preview":True},timeout=20)
    r.raise_for_status(); return True
