"""Audit every tracked Sky file for accidental broker prerequisites in research.

Read-only; scans models, modules, commands, workflow configs, tests and docs.
No provider calls, account access, Production changes or orders.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

BROKER = re.compile(
    r"券商|開戶|證券帳戶|真實持倉|實際持倉|委託.*成交|"
    r"broker(?:age)?|live[_ -]?ledger|broker[_ -]?account|"
    r"P0_R_CURRENT_PORTFOLIO_LEDGER", re.I)
RESEARCH = re.compile(
    r"研究|模擬|當沖|波段|掃描|指令|回測|前瞻|Paper|Shadow|"
    r"research|simulate|simulation|scan|command|strategy|validate|"
    r"risk|portfolio", re.I)
REQUIRED = re.compile(
    r"必須|必要|需先|先確認|前置|不得|無法|必備|需提供|"
    r"require(?:d|ment|s)?|mandatory|must|prerequisite|"
    r"block(?:ed|ing)?|gate|fail.closed", re.I)
LIVE_ONLY = re.compile(
    r"未來|實盤|真實下單|正式實盤|正式交易|"
    r"future[_ -]?live|live[_ -]?trad|production|"
    r"formal|P0.G|P0.R.*正式", re.I)
EXT = {".py", ".md", ".yml", ".yaml", ".json", ".toml", ".txt"}


def inspect_text(path, content):
    matches = []
    for line_no, line in enumerate(content.splitlines(), 1):
        if not BROKER.search(line):
            continue
        cls = ("POSSIBLE_RESEARCH_PREREQUISITE"
               if RESEARCH.search(line) and REQUIRED.search(line)
               and not LIVE_ONLY.search(line)
               and not re.search(r"不(?:需|必須|應)|無須|not required|not a prerequisite|"
                                 r"does not require|not mandatory|不得要求|不再.*必要", line, re.I)
               else "LIVE_ONLY_OR_INFORMATIONAL")
        matches.append({"line": line_no, "class": cls, "text": line.strip()[:350]})
    return matches


def scan(root):
    root = Path(root)
    proc = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    paths = [Path(p.decode()) for p in proc.stdout.split(b"\0") if p]
    scanned, hits, candidates, omitted = 0, [], [], []
    for rel in paths:
        if rel.suffix.lower() not in EXT:
            omitted.append(str(rel))
            continue
        try:
            content = (root / rel).read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            omitted.append(str(rel))
            continue
        scanned += 1
        findings = inspect_text(rel, content)
        if not findings:
            continue
        item = {"path": str(rel), "hits": findings}
        hits.append(item)
        if any(x["class"] == "POSSIBLE_RESEARCH_PREREQUISITE" for x in findings):
            candidates.append(str(rel))
    return {
        "schema": "SKY_BROKERLESS_RESEARCH_REPOSITORY_AUDIT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tracked_text_files_scanned": scanned,
        "tracked_broker_reference_files": len(hits),
        "possible_research_requirement_files": candidates,
        "references": hits,
        "skipped_paths_count": len(omitted),
        "broker_account_required_for_research": False,
        "live_trading_enabled": False,
        "automatic_order": False,
        "verdict": "NEEDS_MANUAL_CLASSIFICATION" if candidates else "NO_POSSIBLE_RESEARCH_PREREQUISITE_FOUND",
        "note": "Static heuristic only, review each candidate. Research must not require a brokerage account; future-live checks are distinct. This is NOT a test of market-data adequacy or model profitability.",
    }


def main():
    repo = Path(__file__).resolve().parents[1]
    report = scan(repo)
    target = repo / "output" / "sky_brokerless_contract"
    target.mkdir(parents=True, exist_ok=True)
    (target / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# Sky 無券商帳戶研究前置條件全庫盤點", "",
             "掃描檔案數：" + str(report["tracked_text_files_scanned"]),
             "提及券商／實盤帳本檔案數：" + str(report["tracked_broker_reference_files"]),
             "研究前置條件疑似檔案數：" + str(len(report["possible_research_requirement_files"])),
             "", "## 需要逐項判斷（非自動判定違規）"]
    for item in report["references"]:
        for hit in item["hits"]:
            if hit["class"] == "POSSIBLE_RESEARCH_PREREQUISITE":
                lines.append(f'- \`{item["path"]}:{hit["line"]}\` {hit["text"]}')
    lines += ["", "研究／Paper 不需要券商帳戶；未來實盤仍禁止下單並需獨立治理。",
              "文字掃描不能證明每個 Python／Workflow 分支在 runtime 的行為；需搭配整合測試。"]
    (target / "latest.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
