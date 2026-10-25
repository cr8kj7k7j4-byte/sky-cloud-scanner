from pathlib import Path

import src.notifier as notifier


class FakeResponse:
    def raise_for_status(self):
        return None


def _configure(monkeypatch, tmp_path):
    monkeypatch.setattr(notifier, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(notifier, "TELEGRAM_CHAT_ID", "test-chat")
    monkeypatch.setattr(notifier, "REDIS_URL", "")
    monkeypatch.setattr(notifier, "ALERT_DELIVERY_LOG", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(notifier, "ALERT_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(notifier, "ALERT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(notifier, "ALERT_RETRY_BASE_SECONDS", 0)
    notifier._LOCAL_DEDUP.clear()


def test_alert_retry_then_success(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary")
        return FakeResponse()

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    assert notifier.send_telegram("retry-test") is True
    assert calls["count"] == 3

    log = Path(notifier.ALERT_DELIVERY_LOG).read_text(encoding="utf-8")
    assert '"delivery_status": "RETRYING"' in log
    assert '"delivery_status": "DELIVERED"' in log


def test_alert_dedup_suppresses_duplicate(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(notifier.requests, "post", fake_post)
    assert notifier.send_telegram("same-message") is True
    assert notifier.send_telegram("same-message") is True
    assert calls["count"] == 1

    log = Path(notifier.ALERT_DELIVERY_LOG).read_text(encoding="utf-8")
    assert '"delivery_status": "DEDUPLICATED"' in log


def test_missing_config_is_logged_and_nonfatal(monkeypatch, tmp_path):
    monkeypatch.setattr(notifier, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(notifier, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(notifier, "ALERT_DELIVERY_LOG", str(tmp_path / "alerts.jsonl"))

    assert notifier.send_telegram("no-config") is False
    log = Path(notifier.ALERT_DELIVERY_LOG).read_text(encoding="utf-8")
    assert '"delivery_status": "SKIPPED_CONFIG"' in log
    assert '"escalation_required": true' in log
