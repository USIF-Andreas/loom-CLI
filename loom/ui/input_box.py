"""Modern input box for the chat REPL, built on prompt_toolkit.

Gives a clean styled prompt with command history and `/` autocompletion
that suggests slash commands. Falls back to plain input() when no TTY
or prompt_toolkit is unavailable.
"""

from __future__ import annotations

import sys

from . import commands as slash

_STYLE = None
_TOOLBAR = ""
_session = None


_cached_ctx: dict | None = None


def set_context(ctx: dict) -> None:
    global _cached_ctx
    _cached_ctx = ctx


def _build_style():
    from prompt_toolkit.styles import Style

    return Style.from_dict({
        "prompt": "bold #a78bfa",
        "bottom-toolbar": "#94a3b8 bg:#1e1b2e",
        "completion-menu": "bg:#2d2d44 #e0e0e0",
        "completion-menu.completion.current": "bg:#5b4a8a #ffffff",
    })


def _status_bar() -> str:
    """Build a status-bar string showing provider, model, workspace, git branch, tokens."""
    ctx = _cached_ctx
    if ctx is None:
        try:
            from ..config import Config
            cfg = Config.load()
            provider = cfg.provider
            model = cfg.model
        except Exception:
            provider = "?"
            model = "?"
    else:
        cfg = ctx.get("config")
        provider = getattr(cfg, "provider", "?") if cfg else "?"
        model = getattr(cfg, "model", "?") if cfg else "?"

    import os
    from pathlib import Path

    wd = Path.cwd().name

    git_branch = "?"
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                          capture_output=True, text=True, timeout=1)
        if r.returncode == 0:
            git_branch = r.stdout.strip()
    except Exception:
        pass

    tokens = "0"
    if ctx:
        t = ctx.get("tokens", {})
        total = (t.get("input", 0) or 0) + (t.get("output", 0) or 0)
        tokens = f"{total:,}" if total else "0"

    return (
        f" loom  ·  {provider}  ·  {model}  "
        f"·  Workspace: {wd}  ·  Git: {git_branch}  ·  Tokens: {tokens}"
    )


def _completer():
    from prompt_toolkit.completion import Completer, Completion

    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            prefix = text[1:]
            for cmd in slash.COMMAND_LIST:
                if cmd.name.startswith(prefix):
                    yield Completion(
                        "/" + cmd.name,
                        start_position=-len(text),
                        display=f"/{cmd.name}  — {cmd.description}",
                    )

    return SlashCompleter()


def _get_session():
    global _session, _STYLE, _TOOLBAR
    if _session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.output import create_output

        _STYLE = _build_style()
        _TOOLBAR = _status_bar()
        output = None
        # Disable CPR (cursor position request) probing — some terminals don't
        # support it and print a "doesn't support cursor position requests"
        # warning. Only relevant for a real TTY Vt100 output.
        try:
            if sys.stdout.isatty():
                from prompt_toolkit.output.vt100 import Vt100_Output

                output = Vt100_Output.from_pty(
                    sys.stdout, term="xterm-256color"
                )
                # Disable CPR probing to avoid the "doesn't support cursor
                # position requests" warning on limited terminals.
                try:
                    output.enable_cpr = False
                except Exception:
                    pass
            else:
                output = create_output(sys.stdout)
        except Exception:
            output = None
        session_kwargs = dict(
            completer=_completer(),
            style=_STYLE,
            bottom_toolbar=_TOOLBAR,
            complete_while_typing=True,
        )
        if output is not None:
            session_kwargs["output"] = output
        _session = PromptSession(**session_kwargs)
    return _session


def read_input(prompt: str = "loom > ") -> str:
    """Read one line using prompt_toolkit when a TTY is available."""
    if not sys.stdin.isatty():
        return input(prompt)
    try:
        return _get_session().prompt(prompt).strip()
    except Exception:
        return input(prompt).strip()
