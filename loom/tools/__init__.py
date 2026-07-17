"""Tool schemas and the tool executor node."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from ..ui import confirm
from . import files, search, shell, web
from .clang import TOOL_SCHEMAS

# Map tool name -> callable.
TOOL_FUNCS: dict[str, Any] = {
    "read_file": files.read_file,
    "write_file": files.write_file,
    "edit_file": files.edit_file,
    "bash": shell.bash,
    "glob": search.glob,
    "grep": search.grep,
    "web_search": web.web_search,
    "fetch_url": web.fetch_url,
}


def execute_tool_call(name: str, tool_input: dict, allow: bool = True) -> str:
    """Execute a single tool and return its string result."""
    func = TOOL_FUNCS.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'"

    # Hard denylist check (applies even in yolo mode).
    if name == "bash":
        cmd = tool_input.get("command", "")
        denied = confirm.is_denied(cmd)
        if denied:
            return f"Error: {denied}"

    if not allow:
        return f"Error: permission denied for tool '{name}'"

    try:
        result = func(**tool_input)
    except Exception as exc:  # surface as tool result text, don't crash the loop
        return f"Error executing {name}: {type(exc).__name__}: {exc}"
    if not isinstance(result, str):
        result = json.dumps(result, default=str)
    return result


def execute_tools(state: dict) -> dict:
    """LangGraph node: run all tool_calls on the last AI message."""
    messages = state["messages"]
    last = messages[-1]
    allow = state.get("permission_result", "allow") != "deny"

    tool_messages: list[ToolMessage] = []
    for call in getattr(last, "tool_calls", []) or []:
        name = call["name"]
        args = call["args"]
        content = execute_tool_call(name, args, allow=allow)
        tool_messages.append(
            ToolMessage(content=content, tool_call_id=call["id"])
        )
    return {"messages": messages + tool_messages}
