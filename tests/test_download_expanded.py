import os
import sys
from datetime import date
from pathlib import Path

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


def test_429_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("FUGLE_API_KEY", "test")
    responses = iter([
        FakeResponse(429),
        FakeResponse(429, headers={"Retry-After": "1"}),
        FakeResponse(200, {"data": [{"close": 10.0}]}),
    ])
    sleeps = []

    def fake_get(*args, **kwargs):
        return next(responses)

    data = _request_chunk(
        "2409",
        date(2026, 1, 1),
        date(2026, 1, 2),
        request_get=fake_get,
        sleep_fn=lambda x: sleeps.append(x),
    )

    assert data == [{"close": 10.0}]
    assert sleeps == [5, 10]


def test_404_chunk_is_empty_not_failure(monkeypatch):
    monkeypatch.setenv("FUGLE_API_KEY", "test")

    data = _request_chunk(
        "7818",
        date(2023, 5, 23),
        date(2024, 4, 17),
        request_get=lambda *args, **kwargs: FakeResponse(404),
        sleep_fn=lambda x: None,
    )

    assert data == []
