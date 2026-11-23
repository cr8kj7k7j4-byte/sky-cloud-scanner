"""Historical Fugle data transport tests; no real provider or GitHub calls."""
import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.download_expanded import _request_chunk


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests import HTTPError
            raise HTTPError(f"{self.status_code} error")


def test_429_is_not_retried_under_paid_atomic_claim(monkeypatch):
    monkeypatch.setenv("FUGLE_API_KEY", "test")
    monkeypatch.setenv("SKY_PAID_ATOMIC_ENFORCE", "1")
    observed = []
    def fake_get(*args, **kwargs):
        observed.append(1)
        return FakeResponse(429)
    with patch("research.download_expanded.guard_fugle_request") as claim:
        import pytest
        with pytest.raises(RuntimeError, match="FUGLE_RATE_LIMITED_NO_RETRY"):
            _request_chunk("2409", date(2026, 1, 1), date(2026, 1, 2),
                           request_get=fake_get, sleep_fn=lambda x: None)
        claim.assert_called_once()
    assert len(observed) == 1


def test_404_chunk_is_empty_after_verified_claim(monkeypatch):
    monkeypatch.setenv("FUGLE_API_KEY", "test")
    monkeypatch.setenv("SKY_PAID_ATOMIC_ENFORCE", "1")
    with patch("research.download_expanded.guard_fugle_request") as claim:
        data = _request_chunk(
            "7818", date(2023, 5, 23), date(2024, 4, 17),
            request_get=lambda *args, **kwargs: FakeResponse(404),
            sleep_fn=lambda x: None,
        )
        claim.assert_called_once()
    assert data == []



def test_main_fails_closed_after_writing_complete_diagnostics(tmp_path, monkeypatch):
    import json
    import pytest
    from research import download_expanded
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sample": [
        {"symbol": "1111"}, {"symbol": "2222"}
    ]}), encoding="utf-8")
    monkeypatch.setenv("SKY_PAID_ATOMIC_ENFORCE", "1")
    monkeypatch.setattr(sys, "argv", ["download_expanded.py", "--manifest", str(manifest),
                                     "--from-date", "2026-01-01", "--to-date", "2026-01-02",
                                     "--out", str(tmp_path / "history")])
    def fake_get_hist(symbol, *_args):
        if symbol == "2222":
            raise RuntimeError("MOCK_PAID_CLAIM_BLOCKED")
        return [{"close": 100}]
    monkeypatch.setattr(download_expanded, "get_hist", fake_get_hist)
    with pytest.raises(SystemExit, match="HISTORICAL_DOWNLOAD_INCOMPLETE: 1/2"):
        download_expanded.main()
    summary = json.loads((tmp_path / "download_summary.json").read_text(encoding="utf-8"))
    assert len(summary) == 2
    assert summary[0]["ok"] is True
    assert summary[1]["ok"] is False
    assert "MOCK_PAID_CLAIM_BLOCKED" in summary[1]["error"]


def test_main_all_failed_or_empty_fails_closed(tmp_path, monkeypatch):
    import json
    import pytest
    from research import download_expanded
    manifest = tmp_path / "manifest.json"
    monkeypatch.setenv("SKY_PAID_ATOMIC_ENFORCE", "1")
    monkeypatch.setattr(sys, "argv", ["download_expanded.py", "--manifest", str(manifest),
                                     "--from-date", "2026-01-01", "--to-date", "2026-01-02",
                                     "--out", str(tmp_path / "history")])
    manifest.write_text(json.dumps({"sample": [{"symbol": "1111"}]}), encoding="utf-8")
    monkeypatch.setattr(download_expanded, "get_hist",
                        lambda *_args: (_ for _ in ()).throw(RuntimeError("MOCK_BLOCKED")))
    with pytest.raises(SystemExit, match="HISTORICAL_DOWNLOAD_INCOMPLETE: 1/1"):
        download_expanded.main()
    assert json.loads((tmp_path / "download_summary.json").read_text())[0]["ok"] is False
    manifest.write_text(json.dumps({"sample": []}), encoding="utf-8")
    with pytest.raises(SystemExit, match="HISTORICAL_DOWNLOAD_INCOMPLETE: 0/0"):
        download_expanded.main()


def test_main_all_success_exits_normally(tmp_path, monkeypatch):
    import json
    from research import download_expanded
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sample": [{"symbol": "1111"}]}), encoding="utf-8")
    monkeypatch.setenv("SKY_PAID_ATOMIC_ENFORCE", "1")
    monkeypatch.setattr(sys, "argv", ["download_expanded.py", "--manifest", str(manifest),
                                     "--from-date", "2026-01-01", "--to-date", "2026-01-02",
                                     "--out", str(tmp_path / "history")])
    monkeypatch.setattr(download_expanded, "get_hist", lambda *_args: [{"close": 100}])
    download_expanded.main()
    assert json.loads((tmp_path / "download_summary.json").read_text())[0]["ok"] is True


def test_paid_guard_blocks_before_http_request(monkeypatch):
    import pytest
    monkeypatch.delenv("SKY_PAID_ATOMIC_ENFORCE", raising=False)
    called = []
    with pytest.raises(RuntimeError, match="HISTORICAL_PAID_GUARD_REQUIRED"):
        _request_chunk("1111", date(2026, 1, 1), date(2026, 1, 2),
                       request_get=lambda *_a, **_kw: called.append(True))
    assert not called
