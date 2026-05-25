import json

import pytest

from src.sdk.client import OrchestratorClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps({"ok": True}).encode()


def test_request_uses_default_timeout(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.delenv("AO_REQUEST_TIMEOUT", raising=False)
    monkeypatch.setattr("src.sdk.client.urlopen", fake_urlopen)

    client = OrchestratorClient(base_url="https://example.test", api_key="key")

    assert client.list_agents() == {"ok": True}
    assert calls[0][1] == OrchestratorClient.DEFAULT_TIMEOUT


def test_request_uses_constructor_timeout(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("src.sdk.client.urlopen", fake_urlopen)

    client = OrchestratorClient(
        base_url="https://example.test",
        api_key="key",
        timeout=2.5,
    )

    assert client.get_agent("agent-1") == {"ok": True}
    assert calls[0][1] == 2.5


def test_request_uses_env_timeout(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setenv("AO_REQUEST_TIMEOUT", "7.25")
    monkeypatch.setattr("src.sdk.client.urlopen", fake_urlopen)

    client = OrchestratorClient(base_url="https://example.test", api_key="key")

    assert client.delete_agent("agent-1") == {"ok": True}
    assert calls[0][1] == 7.25


@pytest.mark.parametrize("bad_timeout", [0, -1, "nan", "inf", "never"])
def test_rejects_invalid_timeout_values(bad_timeout):
    with pytest.raises(ValueError, match="finite positive"):
        OrchestratorClient(timeout=bad_timeout)
