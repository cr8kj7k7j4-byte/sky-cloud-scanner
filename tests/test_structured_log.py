import json

from src.structured_log import emit


def test_structured_log_required_fields(tmp_path):
    path = tmp_path / "system.jsonl"
    payload = emit(
        "scan_completed",
        module="W3B",
        service="scanner",
        request_id="run-1",
        symbol="2409",
        strategy_version="Sky-V2.1",
        severity="INFO",
        latency_ms=12.5,
        path=path,
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())
    required = {
        "timestamp",
        "module",
        "service",
        "symbol",
        "strategy_version",
        "request_id",
        "event",
        "severity",
        "error_type",
        "latency_ms",
    }
    assert required.issubset(row)
    assert row["request_id"] == "run-1"
    assert payload["event"] == "scan_completed"
