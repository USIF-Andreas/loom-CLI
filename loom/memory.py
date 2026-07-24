"""User Memory — remembers preferences across sessions.

Commands:
  /remember <key> <value>  — store a memory
  /forget <key>            — remove a memory
  /memory                  — list all memories
"""

from __future__ import annotations

import json
from pathlib import Path

MEMORY_PATH = Path.home() / ".loom" / "memory.json"


def _load() -> dict:
    if MEMORY_PATH.exists():
        try:
            return json.loads(MEMORY_PATH.read_text())
        except (json.JSONDecodeError, Exception):
            pass
    return {}


def _save(data: dict) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(data, indent=2))


def remember(key: str, value: str) -> str:
    data = _load()
    data[key] = value
    _save(data)
    return f"Remembered: {key} = {value}"


def forget(key: str) -> str:
    data = _load()
    if key in data:
        del data[key]
        _save(data)
        return f"Forgot: {key}"
    return f"No memory found for: {key}"


def list_memories() -> list[tuple[str, str]]:
    data = _load()
    return list(data.items())


def get_memory(key: str) -> str | None:
    data = _load()
    return data.get(key)
