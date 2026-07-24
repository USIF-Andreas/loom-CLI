"""Searchable command palette triggered by `/` in the chat REPL.

Provides a full-screen fuzzy-search menu with categorized commands,
arrow-key navigation, and instant search filtering.
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from . import commands as slash


@dataclass
class PaletteItem:
    label: str
    description: str
    category: str
    handler: str  # slash command name to dispatch


CATEGORIES = [
    "system",
    "model",
    "session",
    "memory",
    "theme",
    "config",
    "plugins",
    "help",
]

ITEMS: list[PaletteItem] = [
    PaletteItem("commands", "List all available commands", "system", "commands"),
    PaletteItem("clear", "Clear the conversation history", "system", "clear"),
    PaletteItem("exit", "Exit the chat session", "system", "exit"),
    PaletteItem("help", "Show help information", "help", "help"),
    PaletteItem("models", "List and pick a model for the current provider", "model", "models"),
    PaletteItem("provider", "Switch provider (groq/openrouter/nvidia/anthropic)", "model", "provider"),
    PaletteItem("architect", "Interactive multi-agent pipeline", "model", "architect"),
    PaletteItem("sessions", "List and resume a past session", "session", "sessions"),
    PaletteItem("graph", "Show project dependency graph", "system", "graph"),
    PaletteItem("index", "Index workspace for smart context", "system", "index"),
    PaletteItem("context", "Show context analysis", "config", "context"),
    PaletteItem("plan", "Toggle planning mode", "config", "plan"),
    PaletteItem("multi", "Multi-agent pipeline", "system", "multi"),
    PaletteItem("serve", "Serve a folder over HTTP", "system", "serve"),
    PaletteItem("goat", "Play pixel goat animation", "system", "goat"),
    PaletteItem("git", "Run a git command", "system", "git"),
    PaletteItem("remember", "Store a memory key/value", "memory", "remember"),
    PaletteItem("forget", "Remove a memory", "memory", "forget"),
    PaletteItem("memory", "List all memories", "memory", "memory"),
    PaletteItem("tools", "List available tools", "system", "tools"),
    PaletteItem("test", "Run tests", "system", "test"),
    PaletteItem("bench", "Run a quick benchmark", "system", "bench"),
    PaletteItem("plugins", "List installed plugins", "plugins", "plugins"),
    PaletteItem("mcp", "List MCP servers", "config", "mcp"),
    PaletteItem("config", "Show current configuration", "config", "config"),
    PaletteItem("export", "Export session history", "session", "export"),
    PaletteItem("checkpoint", "Create a checkpoint", "system", "checkpoint"),
    PaletteItem("checkpoints", "List checkpoints", "system", "checkpoints"),
    PaletteItem("undo", "Roll back to a checkpoint", "system", "undo"),
    PaletteItem("commands", "List all commands", "system", "commands"),
]

CATEGORY_COLORS = {
    "system": "ansiblue",
    "model": "ansigreen",
    "session": "ansiyellow",
    "memory": "ansimagenta",
    "theme": "ansicyan",
    "config": "ansired",
    "plugins": "ansiwhite",
    "help": "ansibrightblack",
}


def _score(text: str, query: str) -> int:
    """Simple fuzzy score: contiguous match > prefix > subsequence."""
    if not query:
        return 100
    text_l = text.lower()
    query_l = query.lower()
    if query_l in text_l:
        idx = text_l.index(query_l)
        return 90 - idx
    if text_l.startswith(query_l):
        return 80
    q_idx = 0
    for ch in text_l:
        if q_idx < len(query_l) and ch == query_l[q_idx]:
            q_idx += 1
    if q_idx == len(query_l):
        return 70 - len(text)
    return 0


def run_command_palette() -> str | None:
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout

    query = [""]
    selected = [0]
    VISIBLE = 15

    def get_filtered():
        q = query[0].strip()
        scored = []
        for item in ITEMS:
            s = _score(item.label, q)
            if s and s >= 30:
                scored.append((s, item))
            for alias in [item.description, item.category]:
                s2 = _score(alias, q)
                if s2 > s:
                    s = s2
                    scored.append((s, item))
        scored.sort(key=lambda x: (-x[0], x[1].label))
        seen = set()
        deduped = []
        for _, item in scored:
            if item.label not in seen:
                seen.add(item.label)
                deduped.append(item)
        return deduped[:50]

    def get_display():
        filtered = get_filtered()
        if not filtered and query[0]:
            return [("ansiwhite", "  No matching commands\n\n  type to search  Esc cancel")]
        if not filtered:
            filtered = [i for i in ITEMS if i.category in ("system", "help")]
        if selected[0] >= len(filtered):
            selected[0] = len(filtered) - 1 if filtered else 0

        cats: dict[str, list[PaletteItem]] = {}
        for item in filtered:
            cats.setdefault(item.category, []).append(item)

        cat_order = [c for c in CATEGORIES if c in cats]
        lines = []
        idx = 0
        for cat in cat_order:
            items = cats[cat]
            color = CATEGORY_COLORS.get(cat, "ansiwhite")
            lines.append((color, f"  {cat}\n"))
            for item in items:
                prefix = "\u25b6 " if idx == selected[0] else "  "
                label = f"{prefix}{item.label}"
                desc = f"  \u2014 {item.description}" if item.description else ""
                nl = "\n" if idx < len(filtered) - 1 else ""
                lines.append(("", f"    {label}{desc}{nl}"))
                idx += 1

        total = len(filtered)
        lines.append(("ansiwhite", f"\n  \u2191\u2193 navigate  type filter  \u23ce execute  Esc close"))
        return lines

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        if selected[0] > 0:
            selected[0] -= 1
        event.app.invalidate()

    @kb.add("down")
    def _(event):
        filtered = get_filtered()
        if not filtered:
            filtered = [i for i in ITEMS if i.category in ("system", "help")]
        if selected[0] < len(filtered) - 1:
            selected[0] += 1
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        filtered = get_filtered()
        if not filtered:
            filtered = [i for i in ITEMS if i.category in ("system", "help")]
        if filtered:
            event.app.exit(result=filtered[selected[0]].handler)

    @kb.add("escape")
    def _(event):
        event.app.exit(result=None)

    @kb.add("backspace")
    def _(event):
        query[0] = query[0][:-1]
        selected[0] = 0
        event.app.invalidate()

    for ch in string.printable:
        if ch in ("\n", "\r", "\t"):
            continue

        @kb.add(ch)
        def _(event, ch=ch):
            query[0] += ch
            selected[0] = 0
            event.app.invalidate()

    app = Application(
        layout=Layout(
            Window(FormattedTextControl(get_display), dont_extend_height=True)
        ),
        key_bindings=kb,
        full_screen=True,
    )
    return app.run()
