"""P0-A research-only: low estimated margin maintenance + rising aggressive-buy snapshots.
No trade execution. No claim of complete consecutive buy trades.
"""
import os
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, time as dtime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
BASE = "https://api.finmindtrade.com/api/v4"

def request_json(url, params=None, token=None, post=None):
    if params is not None:
        url += "?" + urlencode(params)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None if post is None else urlencode(post).encode()
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    with urlopen(Request(url, data=data, headers=headers), timeout=20) as res:
        return json.load(res)

def load_prior_universe(token, today):
    """One EOD dataset query per calendar day; latest prior session only."""
    for delta in range(1, 8):
        day = (today - timedelta(days=delta)).isoformat()
        response = request_json(BASE + "/data",
            {"dataset": "TaiwanStockMarginMaintenance", "start_date": day, "end_date": day}, token)
        if response.get("status") != 200:
            raise RuntimeError("FinMind margin data unauthorized/error: " + str(response.get("msg")))
        rows = [r for r in response.get("data", []) if r.get("date") == day]
        if rows:
            return day, {str(r["stock_id"]): r for r in rows
                if str(r.get("stock_id", "")).isdigit()
                and len(str(r["stock_id"])) == 4
                and float(r.get("margin_maintenance") or 999) < 130
                and float(r.get("margin_balance") or 0) >= 100}
    raise RuntimeError("No prior-session margin data: do not silently use stale list")

def evaluate(samples, row, now):
    """Three DISTINCT buy-side snapshot observations, not every intervening trade."""
    try:
        ts = datetime.fromisoformat(str(row["date"]).replace(" ", "T")).replace(tzinfo=TZ)
        px, vol, direction = float(row["close"]), float(row["total_volume"]), int(row["TickType"])
        bid, ask = float(row["buy_price"]), float(row["sell_price"])
    except (KeyError, ValueError, TypeError):
        return False
    if ts.date() != now.date() or not (0 <= (now-ts).total_seconds() <= 35):
        return False
    if px <= 0 or bid <= 0 or ask < bid or (ask-bid)/px > .005:
        return False
    if samples and ts <= samples[-1][0]:
        return False
    samples.append((ts, px, vol, direction))
    while samples and (ts-samples[0][0]).total_seconds() > 90:
        samples.popleft()
    if len(samples) < 3:
        return False
    a, b, c = list(samples)[-3:]
    return (a[3] == b[3] == c[3] == 1
        and a[1] < b[1] < c[1] and a[2] < b[2] < c[2]
        and (c[1]/a[1]-1)*100 >= .7 and c[2]-a[2] >= 10)

def notify(message, dry_run):
    if dry_run:
        print(message, flush=True)
        return
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    result = request_json("https://api.telegram.org/bot"+token+"/sendMessage",
                          post={"chat_id": chat, "text": message})
    if not result.get("ok"):
        raise RuntimeError("Telegram delivery failed")

def main():
    token = os.environ.get("FINMIND_TOKEN")
    if not token:
        raise RuntimeError("FINMIND_TOKEN absent: monitor stays disabled")
    dry_run = os.getenv("MARGIN_WATCH_DRY_RUN", "1") != "0"
    if not dry_run and not (os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        raise RuntimeError("Missing Telegram credentials")
    day = datetime.now(TZ).date()
    if day.weekday() >= 5:
        print("Market closed: no alerts")
        return
    source_day, universe = load_prior_universe(token, day)
    print(f"RESEARCH ONLY: {len(universe)} stocks, estimated margin as-of {source_day}", flush=True)
    samples, sent_at = defaultdict(lambda: deque(maxlen=10)), {}
    interval = max(10, int(os.getenv("MARGIN_WATCH_POLL_SECONDS", "15")))
    while True:
        now = datetime.now(TZ)
        if now.date() != day or now.time() >= dtime(13, 30):
            break
        if now.time() < dtime(9, 0):
            time.sleep(15)
            continue
        response = request_json(BASE + "/taiwan_stock_tick_snapshot", {"data_id": ""}, token)
        if response.get("status") != 200:
            raise RuntimeError("FinMind snapshot unauthorized/error: " + str(response.get("msg")))
        for row in response.get("data", []):
            sid = str(row.get("stock_id", ""))
            if sid not in universe or not evaluate(samples[sid], row, now):
                continue
            if (now-sent_at.get(sid, now-timedelta(hours=1))).total_seconds() < 600:
                continue
            msg = (f"【Sky 研究警戒｜非買進訊號】\n{sid}｜前日推估融資維持率 "
                   f"{float(universe[sid]['margin_maintenance']):.1f}%（{source_day}）\n"
                   f"連續三個不同時間外盤快照＋價格上升；現價 {row['close']}\n"
                   f"行情時間 {row['date']}｜偵測時間 {now:%Y-%m-%d %H:%M:%S}\n"
                   "快照≠完整逐筆；需確認量能、價格風險及成本後RR。")
            notify(msg, dry_run)
            sent_at[sid] = now
        time.sleep(interval)

if __name__ == "__main__":
    main()
