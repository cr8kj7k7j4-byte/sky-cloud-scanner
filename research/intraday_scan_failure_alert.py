"""Fail-visible Telegram alert for the intraday scan workflow."""
import json
import os
import urllib.request


def send_failure(token, chat_id, run_url, opener=urllib.request.urlopen):
    if not token or not chat_id:
        raise ValueError("Telegram credentials are not configured")
    text = (
        "🔴 Sky 當沖雲端掃描異常\n"
        "本次掃描未完成，請勿將舊結果視為即時訊號。\n"
        f"執行紀錄：{run_url}"
    )
    data = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with opener(request, timeout=20) as response:
        result = json.load(response)
    if result.get("ok") is not True:
        raise RuntimeError("Telegram API did not accept the notification")


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    try:
        send_failure(
            os.environ.get("TELEGRAM_BOT_TOKEN"),
            os.environ.get("TELEGRAM_CHAT_ID"),
            f"https://github.com/{repo}/actions/runs/{run_id}",
        )
    except Exception as exc:
        # Never log exception text: an HTTP error can contain the bot URL.
        print(f"Telegram failure notification failed: {type(exc).__name__}")
        raise SystemExit(1)
    print("Telegram API accepted the failure notification")


if __name__ == "__main__":
    main()
