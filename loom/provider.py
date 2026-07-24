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

    Each entry carries both ``provider`` (the API source actually serving the
    model, e.g. ``groq``) and ``vendor`` (the upstream author encoded in the
    model id's prefix, falling back to the provider when there is no slash).
    Anthropic has no public models listing, so we return its known model set.
    """
    import requests

    config = config or Config.load()

    if config.provider == "anthropic":
        # No public listing API; surface the known models.
        return [
            {"id": m, "provider": "anthropic", "vendor": "anthropic"}
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

    out = []
    for m in models:
        mid = m.get("id") or m.get("name")
        out.append(
            {
                "id": mid,
                # The provider is the API source we queried.
                "provider": config.provider,
                # Keep any upstream vendor embedded in the id (e.g.
                # "openai/gpt-oss-20b" served via groq). Fall back to the
                # active provider for ids with no slash.
                "vendor": model_vendor(mid, fallback=config.provider),
                "context_length": m.get("context_length"),
            }
        )
    return out


def model_vendor(model_id: str | None, fallback: str = "anthropic") -> str:
    """Return the upstream vendor encoded in a model id (the text before '/').

    For ids without a slash there is no separate vendor, so we fall back to the
    active provider name. For example ``"openai/gpt-oss-20b"`` -> ``"openai"``
    while ``"llama-3.3-70b-versatile"`` -> fallback (e.g. groq).
    """
    mid = model_id or ""
    if "/" in mid:
        return mid.split("/", 1)[0]
    return fallback


def model_line_parts(m: dict, active_provider: str | None = None) -> dict:
    """Decide how to label a model line: its provider, vendor and id.

    Always surfaces the *provider* (the API source that actually serves the
    model). When the model id encodes a different upstream vendor (the text
    before the first slash), that vendor is shown too so a user never confuses
    the model's author with the API it runs on -- e.g. ``qwen/qwen3.6-27b``
    (authored by qwen) served *via groq*.

    Returns a dict with keys:
        id, provider, vendor, context_length, note
    where ``note`` is a compact bracket label like ``[groq]`` or
    ``[canopylabs <- groq]`` for renderers to colour.
    """
    mid = m.get("id") or ""
    provider = m.get("provider") or active_provider or ""
    vendor = m.get("vendor") or model_vendor(mid, fallback=provider)

    if vendor and provider and vendor != provider:
        note = f"[{vendor} <- {provider}]"
    elif provider:
        note = f"[{provider}]"
    else:
        note = ""

    return {
        "id": mid,
        "provider": provider,
        "vendor": vendor,
        "context_length": m.get("context_length"),
        "note": note,
    }


def model_usage(msg: Any) -> dict:
    """Extract token usage from a LangChain AIMessage, best-effort.

    Looks first at ``usage_metadata`` (Anthropic / OpenAI-compatible) and then
    at ``response_metadata.token_usage`` (raw OpenAI shape). Returns a dict with
    integer keys ``input`` and ``output`` (0 when nothing is known).
    """
    meta = getattr(msg, "usage_metadata", None) or {}
    inp = int(meta.get("input_tokens", 0) or 0)
    out = int(meta.get("output_tokens", 0) or 0)
    if not inp and not out:
        rm = getattr(msg, "response_metadata", None) or {}
        tu = rm.get("token_usage", {}) or {}
        inp = int(tu.get("prompt_tokens", 0) or 0)
        out = int(tu.get("completion_tokens", 0) or 0)
    return {"input": inp, "output": out}
