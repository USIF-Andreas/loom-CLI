"""Configuration loading for loom.

Reads API keys / defaults from environment variables and an optional
``~/.loom/config.toml`` file. Supports multiple model providers:
anthropic, openrouter, nvidia, groq.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None  # type: ignore


CONFIG_DIR = Path.home() / ".loom"
CONFIG_PATH = CONFIG_DIR / "config.toml"

# Project-local and user-local .env files (KEY=VALUE lines).
ENV_PATHS = [
    Path.cwd() / ".env",
    CONFIG_DIR / ".env",
]

# Default base URLs and environment-variable names per provider.
PROVIDERS: dict[str, dict[str, str]] = {
    "anthropic": {
        "base_url": "",
        "key_env": "ANTHROPIC_API_KEY",
        "key_cfg": "anthropic_api_key",
        "default_model": "claude-sonnet-4-6",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "key_cfg": "openrouter_api_key",
        "default_model": "anthropic/claude-3.5-sonnet",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_API_KEY",
        "key_cfg": "nvidia_api_key",
        "default_model": "meta/llama-3.1-70b-instruct",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "key_cfg": "groq_api_key",
        "default_model": "llama-3.3-70b-versatile",
    },
}


@dataclass
class Config:
    provider: str = "anthropic"
    api_key: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    base_url: str = ""
    permission_mode: str = "confirm"  # "confirm" | "yolo" | "deny"
    max_context_messages: int = 40
    shell_timeout: int = 30

    @classmethod
    def load(cls, provider_override: str | None = None) -> "Config":
        data: dict = {}
        if CONFIG_PATH.exists() and tomllib is not None:
            with open(CONFIG_PATH, "rb") as fh:
                data = tomllib.load(fh)

        provider = provider_override or data.get("provider", "anthropic")
        if provider not in PROVIDERS:
            provider = "anthropic"
        pinfo = PROVIDERS[provider]

        # API key resolution priority:
        #   env var > project .env > ~/.loom/.env > config.toml
        env_keys = load_env_keys()
        api_key = (
            os.environ.get(pinfo["key_env"])
            or env_keys.get(pinfo["key_env"])
            or data.get(pinfo["key_cfg"])
        )
        model = (
            data.get("model")
            or os.environ.get("LOOM_MODEL")
            or env_keys.get("LOOM_MODEL")
            or pinfo["default_model"]
        )
        base_url = data.get("base_url") or pinfo["base_url"]

        cfg = cls(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            permission_mode=data.get("permission_mode", "confirm"),
            max_context_messages=data.get("max_context_messages", 40),
            shell_timeout=data.get("shell_timeout", 30),
        )
        if mode := os.environ.get("LOOM_PERMISSION_MODE") or env_keys.get(
            "LOOM_PERMISSION_MODE"
        ):
            cfg.permission_mode = mode
        if not api_key:
            raise RuntimeError(
                f"No {pinfo['key_env']} found. Set the environment variable, add "
                f"it to a .env file, or add {pinfo['key_cfg']} to ~/.loom/config.toml"
            )
        return cfg


def load_env_keys() -> dict[str, str]:
    """Parse KEY=VALUE pairs from project-local and user-local .env files.

    Does not touch os.environ — callers decide precedence. Returns a dict.
    """
    result: dict[str, str] = {}
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in result:  # first file wins
                result[key] = val
    return result


@dataclass
class ProviderSpec:
    name: str
    api_key: str
    model: str
    base_url: str


def get_provider_spec() -> ProviderSpec:
    """Return the resolved provider spec from config."""
    cfg = Config.load()
    return ProviderSpec(
        name=cfg.provider,
        api_key=cfg.api_key,
        model=cfg.model,
        base_url=cfg.base_url,
    )
