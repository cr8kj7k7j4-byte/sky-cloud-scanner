
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--download-summary", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    history = Path(args.history_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    summary = json.loads(Path(args.download_summary).read_text(encoding="utf-8"))

    expected = {x["symbol"] for x in manifest.get("sample", [])}
    ok = {x["symbol"] for x in summary if x.get("ok")}
    failed = [x for x in summary if not x.get("ok")]

    files = list(history.glob("*_5.json"))
    file_symbols = {p.name.split("_")[0] for p in files}

    bars_total = 0
    empty_files = []
    parse_errors = []

    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            n = len(obj.get("data", []))
            bars_total += n
            if n == 0:
                empty_files.append(p.name)
        except Exception as e:
            parse_errors.append({"file": p.name, "error": f"{type(e).__name__}: {e}"})

    report = {
        "expected_symbols": len(expected),
        "successful_downloads": len(ok),
        "history_files": len(files),
        "total_5m_bars": bars_total,
        "failed_downloads": failed,
        "missing_files": sorted(expected - file_symbols),
        "unexpected_files": sorted(file_symbols - expected),
        "empty_files": empty_files,
        "parse_errors": parse_errors,
        "validation_pass": (
            len(expected) > 0 and
            len(ok) == len(expected) and
            len(files) == len(expected) and
            not failed and
            not (expected - file_symbols) and
            not empty_files and
            not parse_errors
        )
    }

    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not report["validation_pass"]:
        raise SystemExit("Historical export validation failed.")

if __name__ == "__main__":
    main()
