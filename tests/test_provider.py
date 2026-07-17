"""Tests for multi-provider model building."""

from __future__ import annotations

from unittest.mock import patch

from loom import provider
from loom.config import Config, PROVIDERS


def test_anthropic_model():
    spec = provider.ProviderSpec(
        name="anthropic", api_key="x", model="claude-sonnet-4-6", base_url=""
    )
    with patch("langchain_anthropic.ChatAnthropic") as mock:
        provider.build_chat_model(spec=spec)
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["anthropic_api_key"] == "x"


def test_openrouter_model():
    spec = provider.ProviderSpec(
        name="openrouter",
        api_key="x",
        model="anthropic/claude-3.5-sonnet",
        base_url=PROVIDERS["openrouter"]["base_url"],
    )
    with patch("langchain_openai.ChatOpenAI") as mock:
        provider.build_chat_model(spec=spec)
        mock.assert_called_once()
        _, kwargs = mock.call_args
        assert kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert kwargs["api_key"] == "x"


def test_nvidia_model():
    spec = provider.ProviderSpec(
        name="nvidia",
        api_key="x",
        model="meta/llama-3.1-70b-instruct",
        base_url=PROVIDERS["nvidia"]["base_url"],
    )
    with patch("langchain_openai.ChatOpenAI") as mock:
        provider.build_chat_model(spec=spec)
        _, kwargs = mock.call_args
        assert kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_groq_model():
    spec = provider.ProviderSpec(
        name="groq",
        api_key="x",
        model="llama-3.3-70b-versatile",
        base_url=PROVIDERS["groq"]["base_url"],
    )
    with patch("langchain_openai.ChatOpenAI") as mock:
        provider.build_chat_model(spec=spec)
        _, kwargs = mock.call_args
        assert kwargs["base_url"] == "https://api.groq.com/openai/v1"


def test_config_defaults_per_provider(monkeypatch):
    cfg = Config(provider="groq", api_key="abc", model="llama-3.3-70b-versatile",
                 base_url=PROVIDERS["groq"]["base_url"])
    assert cfg.provider == "groq"
    assert cfg.model == "llama-3.3-70b-versatile"
