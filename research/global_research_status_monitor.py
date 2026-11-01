"""Research intake change detection; never creates trading signals."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def status(issue):
    if not isinstance(issue, dict) or issue.get("number") != 190:
        raise ValueError("unexpected research issue")
    state = {
        "number": 190,
        "state": issue.get("state"),
        "updated_at": issue.get("updated_at"),
        "body_sha256": hashlib.sha256((issue.get("body") or "").encode()).hexdigest(),
        "comments": issue.get("comments"),
        "url": issue.get("html_url"),
    }
    if not state["state"] or not state["updated_at"] or not state["url"]:
        raise ValueError("incomplete research issue")
    return state


def changed(current, previous):
    return not previous or any(current.get(k) != previous.get(k) for k in
                               ("state", "updated_at", "body_sha256", "comments"))


def get_issue(repo):
    result = subprocess.run(["gh", "api", f"repos/{repo}/issues/190"],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    current = status(get_issue(repo))
    previous_file = Path("previous/global-research-state.json")
    try:
        previous = json.loads(previous_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        previous = {}
    Path("output").mkdir(exist_ok=True)
    Path("output/global-research-state.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    if not changed(current, previous):
        print("No research issue changes.")
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise SystemExit("Telegram configuration unavailable; issue change not delivered")
    message = (
        "🟡 Sky 跨市場研究進度｜議題狀態更新\n"
        f"議題：{current['state']}｜更新：{current['updated_at']}\n"
        "此通知僅表示研究議題有變化，不代表資料或回測已通過，"
        "不代表交易策略有效；請查閱最新議題與驗證產物。\n"
        f"{current['url']}"
    )
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": message}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        if result.get("ok") is not True:
            raise RuntimeError("Telegram rejected delivery")
    except Exception as exc:
        print("Notification failed: " + type(exc).__name__)
        raise SystemExit(1)
    print("Telegram accepted research status update")


if __name__ == "__main__":
    main()
