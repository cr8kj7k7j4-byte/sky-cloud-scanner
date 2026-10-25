from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

BASE = "https://mops.twse.com.tw/mops/assets/"
ASSETS = ["t51sb10.js", "home.js"]


def fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 SkyResearchBot/1.0",
            "Accept-Language": "zh-TW,zh;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="ignore")


def extract(asset_name: str, text: str) -> dict:
    api_paths = sorted(set(re.findall(r"/mops/api/[A-Za-z0-9_./?=&-]+", text)))
    web_paths = sorted(set(re.findall(r"/mops/web/[A-Za-z0-9_./?=&-]+", text)))
    ajax_names = sorted(set(re.findall(r"ajax_[A-Za-z0-9_]+", text)))
    keywords = {}
    for kw in [
        "t51sb10",
        "marketKind",
        "count",
        "year",
        "month",
        "date",
        "startDate",
        "endDate",
        "query",
        "history",
        "moreInfoUrl",
        "parameters",
    ]:
        positions = [m.start() for m in re.finditer(kw, text)]
        snippets = []
        for pos in positions[:20]:
            snippets.append(text[max(0, pos - 250): pos + 500])
        keywords[kw] = snippets
    return {
        "asset": asset_name,
        "size": len(text),
        "api_paths": api_paths,
        "web_paths": web_paths,
        "ajax_names": ajax_names,
        "keywords": keywords,
    }


def main():
    out = Path("output/mops_backfill_discovery")
    out.mkdir(parents=True, exist_ok=True)
    report = {"assets": []}

    for asset in ASSETS:
        url = BASE + asset
        text = fetch(url)
        (out / asset).write_text(text, encoding="utf-8")
        report["assets"].append(extract(asset, text))

    (out / "discovery.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for item in report["assets"]:
        print(item["asset"], "size=", item["size"])
        print("API", item["api_paths"][:50])
        print("WEB", item["web_paths"][:50])
        print("AJAX", item["ajax_names"][:50])


if __name__ == "__main__":
    main()
