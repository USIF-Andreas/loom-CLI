"""MCP (Model Context Protocol) support.

Connects to MCP servers for filesystem, GitHub, browser, and other tools.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

MCP_CONFIG_PATH = Path.home() / ".loom" / "mcp.json"


def load_config() -> dict:
    if MCP_CONFIG_PATH.exists():
        try:
            return json.loads(MCP_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def save_config(config: dict) -> None:
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def list_servers() -> list[dict]:
    config = load_config()
    return [{"name": k, **v} for k, v in config.get("servers", {}).items()]


def call_tool(server: str, tool: str, args: dict) -> str:
    config = load_config()
    servers = config.get("servers", {})
    if server not in servers:
        return f"Server '{server}' not found"

    info = servers[server]
    cmd = info.get("command", "")
    if not cmd:
        return f"No command configured for server '{server}'"

    payload = json.dumps({"tool": tool, "args": args})
    try:
        r = subprocess.run(
            cmd.split() + [payload],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout or r.stderr or "No output"
    except Exception as exc:
        return f"Error calling {server}.{tool}: {exc}"