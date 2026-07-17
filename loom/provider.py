"""Model client abstraction supporting multiple providers.

Anthropic uses ChatAnthropic; OpenAI-compatible providers (OpenRouter,
NVIDIA, Groq) use ChatOpenAI pointed at their base URLs. This keeps the rest
of the agent loop provider-agnostic.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from .config import Config, ProviderSpec


def build_chat_model(
    spec: ProviderSpec | None = None,
    config: Config | None = None,
    streaming: bool = True,
    max_tokens: int = 8192,
) -> BaseChatModel:
    """Return a LangChain chat model for the active provider."""
    if spec is None:
        config = config or Config.load()
        spec = ProviderSpec(
            name=config.provider,
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
        )

    if spec.name == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=spec.model,
            streaming=streaming,
            anthropic_api_key=spec.api_key,
            max_tokens=max_tokens,
        )

    # OpenAI-compatible providers often cap max_tokens far below 8192
    # (e.g. Groq/OpenAI many models cap at 4096). Use a safe default.
    provider_max = 4096 if spec.name in ("groq", "openrouter", "nvidia") else max_tokens

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=spec.model,
        streaming=streaming,
        api_key=spec.api_key,
        base_url=spec.base_url or None,
        max_tokens=provider_max,
        default_headers=_provider_headers(spec.name),
    )


def _provider_headers(name: str) -> dict[str, str]:
    if name == "openrouter":
        return {"HTTP-Referer": "https://github.com/loom", "X-Title": "loom"}
    return {}


def list_models(config: Config | None = None) -> list[dict]:
    """Return a list of available models from the provider's /models endpoint.

    Anthropic has no public models listing, so we return its known model set.
    """
    import requests

    config = config or Config.load()

    if config.provider == "anthropic":
        # No public listing API; surface the known models.
        return [
            {"id": m, "provider": "anthropic"}
            for m in [
                "claude-sonnet-4-6",
                "claude-opus-4",
                "claude-3-5-sonnet",
                "claude-3-5-haiku",
            ]
        ]

    url = (config.base_url.rstrip("/") + "/models") if config.base_url else ""
    if not url:
        raise RuntimeError("No base URL configured for this provider.")

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    models = data.get("data", data if isinstance(data, list) else [])
    return [
        {
            "id": m.get("id") or m.get("name"),
            "provider": config.provider,
            "context_length": m.get("context_length"),
        }
        for m in models
    ]
