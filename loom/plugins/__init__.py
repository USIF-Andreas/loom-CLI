"""Plugin system for loom. Plugins can register tools, commands, and hooks.

Commands:
  /plugins         — list installed plugins
  /plugin install  — install a plugin
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

PLUGIN_DIR = Path.home() / ".loom" / "plugins"
_registry: dict[str, dict] = {}


class Plugin:
    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    def execute(self, action: str, **kwargs) -> str:
        raise NotImplementedError

    def register(self) -> dict:
        return {"name": self.name, "version": self.version, "description": self.description}


def discover() -> list[dict]:
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    plugins = []
    for path in PLUGIN_DIR.glob("*.py"):
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
                    instance = obj()
                    info = instance.register()
                    _registry[info["name"]] = {"instance": instance, "info": info, "path": str(path)}
                    plugins.append(info)
        except Exception as exc:
            plugins.append({"name": path.stem, "version": "?", "description": f"Error: {exc}"})
    return plugins


def list_plugins() -> list[dict]:
    if not _registry:
        discover()
    return [v["info"] for v in _registry.values()]


def run_hook(hook: str, **kwargs) -> list[str]:
    results = []
    for name, entry in _registry.items():
        try:
            result = entry["instance"].execute(hook, **kwargs)
            results.append(f"{name}: {result}")
        except Exception as exc:
            results.append(f"{name}: error - {exc}")
    return results