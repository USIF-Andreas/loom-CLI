"""Modern input box for the chat REPL, built on prompt_toolkit.

Gives a colored `you>` prompt, command history, and `/` autocompletion
that suggests the slash commands. Falls back to plain input() when no TTY
or prompt_toolkit is unavailable.
"""

from __future__ import annotations

import sys

from . import commands as slash

_STYLE = None
_TOOLBAR = ""
_session = None


def _build_style():
    from prompt_toolkit.styles import Style

    return Style.from_dict({
        "prompt": "bold ansigreen",
        "bottom-toolbar": "ansibrightblack",
    })


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
                        display=f"/{cmd.name}  - {cmd.description}",
                    )

    return SlashCompleter()


def _get_session():
    global _session, _STYLE, _TOOLBAR
    if _session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.output import create_output

        _STYLE = _build_style()
        _TOOLBAR = "commands: " + slash.menu_text() + "   (Ctrl-C to exit)"
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


def read_input(prompt: str = "you> ") -> str:
    """Read one line using prompt_toolkit when a TTY is available."""
    if not sys.stdin.isatty():
        return input(prompt)
    try:
        return _get_session().prompt(prompt).strip()
    except Exception:
        return input(prompt).strip()
