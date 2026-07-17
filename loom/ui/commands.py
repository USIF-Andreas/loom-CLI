"""Slash-command registry for the interactive chat.

Commands open by typing `/` (the REPL prints the menu). `/commands` is
intentionally listed first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class SlashCommand:
    name: str
    description: str
    handler: Callable[["ChatController"], None]


class ChatController:
    """Handle passed to command handlers (avoids circular imports)."""

    def __init__(self, ctx: dict) -> None:
        self.ctx = ctx

    @property
    def history(self):
        return self.ctx["history"]

    def clear_history(self) -> None:
        self.ctx["history"].clear()

    def print(self, role: str, text: str) -> None:
        self.ctx["print"](role, text)

    def exit(self) -> None:
        self.ctx["exit"] = True


def _cmd_commands(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_commands")
    if picker is not None:
        picker()  # use the chat's numbered command picker (consistent for /commands and /com)
    else:
        from . import commands as _cmds

        ctrl.print("system", "Available commands:")
        for c in _cmds.COMMAND_LIST:
            ctrl.print("system", f"  /{c.name}  - {c.description}")


def _cmd_clear(ctrl: ChatController) -> None:
    ctrl.clear_history()
    ctrl.print("system", "Conversation history cleared.")


def _cmd_models(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_models")
    if picker is not None:
        picker()  # use the chat's numbered picker (consistent for /models and /mod)
    else:
        from ..cli import _cmd_models as run_models

        run_models(ctrl.ctx.get("provider"))


def _cmd_provider(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_providers")
    if picker is not None:
        picker()  # chat's numbered provider picker
    else:
        ctrl.print("system", f"Current provider: {ctrl.ctx.get('provider')}")


def _cmd_help(ctrl: ChatController) -> None:
    ctrl.print(
        "system",
        "Type a task for the agent, or `/` to see commands. `/commands` lists all.",
    )


def _cmd_exit(ctrl: ChatController) -> None:
    ctrl.exit()


def _cmd_serve(ctrl: ChatController) -> None:
    from ..cli import _serve_command as run_serve

    # Optional path argument: "/serve portfolio"
    args = ctrl.ctx.get("_last_args", [])
    path = args[0] if args else "."
    run_serve(path)


COMMANDS: dict[str, SlashCommand] = {}


def _register(name, description, handler):
    COMMANDS[name] = SlashCommand(name, description, handler)


_register("commands", "list all available commands", _cmd_commands)
_register("clear", "clear the conversation history", _cmd_clear)
_register("models", "list models for the current provider", _cmd_models)
_register("provider", "switch provider (groq/openrouter/nvidia/anthropic)", _cmd_provider)
_register("serve", "serve a folder over http (e.g. /serve portfolio)", _cmd_serve)
_register("help", "show help", _cmd_help)
_register("exit", "exit the chat", _cmd_exit)

COMMAND_LIST = [
    COMMANDS["commands"],
    COMMANDS["clear"],
    COMMANDS["models"],
    COMMANDS["provider"],
    COMMANDS["serve"],
    COMMANDS["help"],
    COMMANDS["exit"],
]


def get_command(name: str) -> SlashCommand | None:
    return COMMANDS.get(name)


def resolve_command(text: str) -> SlashCommand | None:
    """Resolve a typed command, supporting unique prefixes (e.g. /m -> /models)."""
    if not text or not text.startswith("/"):
        return None
    token = text[1:].split()[0]
    if not token:
        return None
    # Exact match first.
    if token in COMMANDS:
        return COMMANDS[token]
    # Unique prefix match.
    matches = [c for c in COMMANDS.values() if c.name.startswith(token)]
    if len(matches) == 1:
        return matches[0]
    return None


def is_command(text: str) -> bool:
    return resolve_command(text) is not None


def menu_text() -> str:
    return "  ".join(f"/{c.name}" for c in COMMAND_LIST)
