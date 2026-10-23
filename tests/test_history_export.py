
import json, tempfile
from pathlib import Path
import subprocess, sys

def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        hist = td / "history"
        hist.mkdir()

        manifest = {
            "sample": [
                {"symbol":"1101","exchange":"TWSE"},
                {"symbol":"5483","exchange":"TPEx"},
            ]
        }
        summary = [
            {"symbol":"1101","ok":True,"bars":2},
            {"symbol":"5483","ok":True,"bars":2},
        ]
        (td/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (td/"summary.json").write_text(json.dumps(summary), encoding="utf-8")

        for s in ("1101","5483"):
            (hist/f"{s}_5.json").write_text(json.dumps({
                "symbol":s,
                "data":[
                    {"date":"2026-01-02T09:05:00+08:00","open":1,"high":1,"low":1,"close":1,"volume":1,"average":1},
                    {"date":"2026-01-02T09:10:00+08:00","open":1,"high":1,"low":1,"close":1,"volume":1,"average":1}
                ]
            }), encoding="utf-8")

        out = td/"validation.json"
        p = subprocess.run([
            sys.executable, "research/validate_history_export.py",
            "--history-dir", str(hist),
            "--manifest", str(td/"manifest.json"),
            "--download-summary", str(td/"summary.json"),
            "--out", str(out)
        ], capture_output=True, text=True)

        assert p.returncode == 0, p.stderr
        r = json.loads(out.read_text(encoding="utf-8"))
        assert r["validation_pass"] is True
        assert r["expected_symbols"] == 2
        assert r["history_files"] == 2
        assert r["total_5m_bars"] == 4

    print("PASS 4/4 historical export unit tests")

if __name__ == "__main__":
    main()
