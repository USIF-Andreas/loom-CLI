"""Tests for the interactive chat commands + streaming wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from loom import agent as agent_pkg
from loom.agent.graph import run_agent_streaming
from loom.ui import commands as cmd


def test_commands_listed_with_commands_first():
    assert cmd.COMMAND_LIST[0].name == "commands"
    names = [c.name for c in cmd.COMMAND_LIST]
    assert names == ["commands", "clear", "models", "provider", "serve", "help", "exit"]


def test_menu_text_has_all():
    text = cmd.menu_text()
    for name in ("commands", "clear", "models", "provider", "serve", "help", "exit"):
        assert f"/{name}" in text


def test_is_command():
    assert cmd.is_command("/clear")
    assert cmd.is_command("/commands")
    assert not cmd.is_command("/nope")
    assert not cmd.is_command("not a command")


def test_clear_command_clears_history():
    ctx = {"history": [MagicMock(), MagicMock()], "print": lambda *a, **k: None}
    ctrl = cmd.ChatController(ctx)
    cmd._cmd_clear(ctrl)
    assert ctx["history"] == []


def test_exit_command_sets_flag():
    ctx = {"exit": False, "print": lambda *a, **k: None}
    ctrl = cmd.ChatController(ctx)
    cmd._cmd_exit(ctrl)
    assert ctx["exit"] is True


def test_commands_handler_lists_all():
    seen = []
    ctx = {"print": lambda r, t: seen.append((r, t)), "provider": "groq"}
    ctrl = cmd.ChatController(ctx)
    cmd._cmd_commands(ctrl)
    assert any("/commands" in t for _, t in seen)


def test_streaming_calls_on_token():
    from langchain_core.messages import AIMessage

    captured = []

    def fake_graph(config, mode):
        graph = MagicMock()
        ai = AIMessage(content="hello world")
        graph.stream = lambda state, stream_mode="messages": iter([(ai, None)])
        ai2 = AIMessage(content="hello world")
        graph.invoke = lambda state: {"messages": state["messages"] + [ai2]}
        return graph

    with patch.object(agent_pkg.graph, "build_graph", fake_graph):
        run_agent_streaming(
            prompt="hi",
            config=MagicMock(provider="groq", model="x", api_key="x"),
            on_token=captured.append,
        )
    assert "".join(captured).strip() == "hello world"
