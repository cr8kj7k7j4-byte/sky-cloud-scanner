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
