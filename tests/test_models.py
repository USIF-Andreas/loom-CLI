"""Tests for the models-listing feature."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from loom.config import Config, PROVIDERS
from loom.provider import list_models


def _cfg(provider: str, key: str) -> Config:
    p = PROVIDERS[provider]
    return Config(
        provider=provider,
        api_key=key,
        model=p["default_model"],
        base_url=p["base_url"],
    )


def test_groq_list_models():
    cfg = _cfg("groq", "x")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "data": [
            {"id": "llama-3.3-70b-versatile", "context_length": 131072},
            {"id": "llama-3.1-8b-instant", "context_length": 131072},
        ]
    }
    fake_resp.raise_for_status.return_value = None
    with patch("requests.get", return_value=fake_resp) as mock_get:
        result = list_models(cfg)
    mock_get.assert_called_once()
    assert len(result) == 2
    assert result[0]["id"] == "llama-3.3-70b-versatile"
    assert result[0]["context_length"] == 131072


def test_anthropic_static_list():
    cfg = _cfg("anthropic", "x")
    with patch("requests.get") as mock_get:
        result = list_models(cfg)
    mock_get.assert_not_called()
    assert any(m["id"] == "claude-sonnet-4-6" for m in result)


def test_openrouter_list_models():
    cfg = _cfg("openrouter", "x")
    fake_resp = MagicMock()
    fake_resp.json.return_value = {
        "data": [{"id": "anthropic/claude-3.5-sonnet"}]
    }
    fake_resp.raise_for_status.return_value = None
    with patch("requests.get", return_value=fake_resp):
        result = list_models(cfg)
    assert result[0]["id"] == "anthropic/claude-3.5-sonnet"
