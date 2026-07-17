"""LangGraph agent definition with tool-use loop, permissions, and streaming."""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langgraph.graph import END, StateGraph

from ..config import Config
from ..tools import execute_tools
from ..tools.clang import TOOL_SCHEMAS as SCHEMAS
from ..ui import confirm as confirm_ui
from ..ui import render

WORKDIR_IGNORED = {"read_file", "glob", "grep", "web_search", "fetch_url"}  # read-only tools


def build_graph(config: Config, permission_mode: str = "confirm"):
    """Build and compile the LangGraph app."""
    from ..provider import build_chat_model

    model = build_chat_model(config=config)
    model = model.bind_tools(SCHEMAS)

    def call_model(state: dict) -> dict:
        messages = state["messages"]
        response: BaseMessage = model.invoke(messages)
        return {"messages": messages + [response]}

    def should_continue(state: dict) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    def tools_with_permission(state: dict) -> dict:
        """Wrapper that asks for permission before running write/shell tools."""
        last: AIMessage = state["messages"][-1]
        allow = True
        for call in last.tool_calls or []:
            name = call["name"]
            if name in WORKDIR_IGNORED or permission_mode == "yolo":
                continue
            if permission_mode == "deny":
                allow = False
                continue
            # confirm mode
            detail = _describe(call)
            # Hard denylist -> always deny.
            if name == "bash" and confirm_ui.is_denied(call["args"].get("command", "")):
                allow = False
                render.render_error(f"Denied by safety denylist: {detail}")
                continue
            if confirm_ui.needs_permission(name, call["args"]):
                ans = render.confirm_prompt(f"Run: {detail}")
                if ans == "always":
                    permission_mode_local = "yolo"  # noqa: F841
                if ans != "allow" and ans != "always":
                    allow = False
        return execute_tools({**state, "permission_result": "allow" if allow else "deny"})

    builder = StateGraph(dict)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tools_with_permission)
    builder.set_entry_point("agent")
    builder.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    builder.add_edge("tools", "agent")
    return builder.compile()


def _describe(call: dict) -> str:
    name = call["name"]
    args = call["args"]
    if name == "bash":
        return args.get("command", "")
    if name == "read_file":
        return f"read {args.get('path')}"
    if name in ("write_file", "edit_file"):
        return f"{name} {args.get('path')}"
    return name


def run_agent(
    prompt: str,
    config: Optional[Config] = None,
    session_id: str = "",
    working_dir: str = ".",
    permission_mode: str = "confirm",
    project_summary: str = "",
) -> list[BaseMessage]:
    """Run one full agent turn (loops until the model stops calling tools)."""
    from ..agent.prompts import build_system_prompt

    config = config or Config.load()
    app = build_graph(config, permission_mode)

    from ..session.tree import project_tree

    if not project_summary:
        project_summary = project_tree(working_dir)

    system = SystemMessage(content=build_system_prompt(project_summary, working_dir))
    messages: list[BaseMessage] = [system, HumanMessage(content=prompt)]

    state = {
        "messages": messages,
        "session_id": session_id,
        "working_dir": working_dir,
        "permission_result": "allow",
    }

    final_state = app.invoke(state)

    # Stream-style rendering of the final assistant message.
    for msg in final_state["messages"]:
        if isinstance(msg, AIMessage) and msg.content:
            render.render_text("assistant", _content_str(msg.content))
    return final_state["messages"]


def _content_str(content) -> str:
    if isinstance(content, str):
        return content
    # list of content blocks
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(parts)


def run_agent_streaming(
    prompt: str,
    config: Optional[Config] = None,
    session_id: str = "",
    working_dir: str = ".",
    permission_mode: str = "confirm",
    project_summary: str = "",
    history: Optional[list] = None,
    on_token: Optional[callable] = None,
) -> list[BaseMessage]:
    """Run the agent loop, streaming tokens/tools live.

    If ``on_token`` is provided it is called with each incremental text chunk
    (used by the TUI). Otherwise output prints to the console. Returns the full
    message list (mutate ``history`` in place for multi-turn chat).
    """
    from ..agent.prompts import build_system_prompt
    from ..session.tree import project_tree

    config = config or Config.load()
    app = build_graph(config, permission_mode)

    if not project_summary:
        project_summary = project_tree(working_dir)

    if history:
        system = SystemMessage(content=build_system_prompt(project_summary, working_dir))
        messages: list[BaseMessage] = [system] + list(history)
    else:
        system = SystemMessage(content=build_system_prompt(project_summary, working_dir))
        messages = [system, HumanMessage(content=prompt)]

    state = {
        "messages": messages,
        "session_id": session_id,
        "working_dir": working_dir,
        "permission_result": "allow",
    }

    last_assistant = ""
    for chunk in app.stream(state, stream_mode="messages"):
        msg, _ = chunk
        if isinstance(msg, AIMessage):
            text = _content_str(msg.content)
            if text:
                new = text[len(last_assistant):]
                if new:
                    if on_token:
                        on_token(new)
                    else:
                        render.console.print(new, end="", style="bright_blue")
                last_assistant = text
            for call in getattr(msg, "tool_calls", None) or []:
                if on_token:
                    on_token(f"\n⚙ {call['name']}({call['args']})\n")
                else:
                    render.render_role("tool_call", f"→ {call['name']}({call['args']})")
    if not on_token:
        render.console.print()  # newline after streamed text

    # Final full state for returning complete history.
    final_state = app.invoke(state)
    return final_state["messages"]
