"""Permission prompts and the destructive-command denylist."""

from __future__ import annotations

import re
from typing import Optional

# Patterns that are always blocked, even in yolo mode.
DENY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/"),               # rm -rf / (any path under root)
    re.compile(r"\brm\s+-rf\s+/+\s*$"),          # rm -rf / only
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}"),  # fork bomb
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}"),  # fork bomb
    re.compile(r">\s*/dev/sda"),                 # overwrite disk
    re.compile(r"mkfs\."),                       # format filesystem
    re.compile(r"\bdd\s+if=.*of=/dev/"),         # dd to device
    re.compile(r"\bshutdown\b|\bhalt\b|\breboot\b|\bpoweroff\b"),
]

# Patterns that should trigger a confirm even in normal mode.
SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bgit\s+push\s+(--force|-f)\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bchmod\s+-R\b"),
    re.compile(r"\bmv\s+.*\s+/\b"),
]

# Mapping of tool name -> should it require permission for write/shell?
WRITE_TOOLS = {"write_file", "edit_file", "bash"}


def is_denied(command: str) -> Optional[str]:
    """Return a reason string if the command is on the hard denylist."""
    for pat in DENY_PATTERNS:
        if pat.search(command):
            return f"Blocked by safety denylist: matches {pat.pattern!r}"
    return None


def is_sensitive(command: str) -> bool:
    return any(p.search(command) for p in SENSITIVE_PATTERNS)


def needs_permission(tool_name: str, tool_input: dict) -> bool:
    """Decide whether a tool call needs user confirmation."""
    if tool_name not in WRITE_TOOLS:
        return False
    cmd = tool_input.get("command", "")
    if cmd and is_denied(cmd):
        return True  # will be denied regardless, but surface it
    return True
