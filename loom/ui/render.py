"""Rich-based terminal rendering with clean, Claude-CLI-inspired styling.

Provides role-based text rendering, tool call/result display, animated
thinking spinners with goat mascot, and permission prompts.
"""

from __future__ import annotations

import sys
import threading
import time

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from .goat import get_mini_goat_frame

console = Console()

# ── Muted, sophisticated 256-color palette ──────────────────────────────────

ROLE_COLORS = {
    "user": "color(114)",       # soft green
    "assistant": "color(147)",  # soft lavender
    "tool_call": "color(222)",  # warm amber
    "tool_result": "color(117)",# sky blue
    "system": "color(245)",     # warm gray
    "error": "color(203)",      # soft red
}

_BORDER = "color(240)"  # subtle border gray

_spinner_lock = threading.Lock()
_spinner_running = False
_spinner_paused = False


# ── Role & text rendering ───────────────────────────────────────────────────

def render_role(role: str, text: str) -> None:
    color = ROLE_COLORS.get(role, "color(245)")
    console.print(Text(f"❯ {role}", style=f"bold {color}"))


def render_text(role: str, text: str) -> None:
    color = ROLE_COLORS.get(role, "color(245)")
    console.print(Text(text, style=color))


# ── Code & diff rendering ──────────────────────────────────────────────────

def render_code(content: str, lexer: str = "python") -> None:
    console.print(Syntax(content, lexer, theme="monokai", word_wrap=True))


def render_diff(diff_text: str) -> None:
    console.print(Panel(
        diff_text,
        title="diff",
        border_style=_BORDER,
        box=box.ROUNDED,
        padding=(0, 1),
    ))


def render_error(msg: str) -> None:
    console.print(Text(f"  ✗ {msg}", style="color(203)"))


# ── Tool call & result rendering ────────────────────────────────────────────

def render_tool_call(name: str, args: dict) -> None:
    """Render a tool call as a compact, Claude-CLI-style indicator."""
    color = ROLE_COLORS["tool_call"]
    console.print(f"\n  [bold {color}]⏺ {name}[/]")
    if isinstance(args, dict):
        for k, v in args.items():
            val = repr(v) if not isinstance(v, str) else v
            if len(val) > 60:
                val = val[:57] + "..."
            console.print(f"  [{_BORDER}]│[/] [dim]{k}[/]={val}")


def render_tool_result(name: str, result: str) -> None:
    """Render a tool result as a compact summary line."""
    body = str(result)
    # Collapse to single line for display
    body = " ".join(body.split())
    if len(body) > 80:
        body = body[:77] + "..."
    console.print(f"  [bold color(117)]✔ {name}[/] [dim]— {body}[/]")


def render_file_op(operation: str, path: str) -> None:
    """Render a file operation with diff-style coloring.

    Args:
        operation: '+' for add, '-' for delete, '~' for edit.
        path: The file path.
    """
    styles = {"+": "bold color(114)", "-": "bold color(203)", "~": "bold color(222)"}
    style = styles.get(operation, "dim")
    console.print(f"  [{style}]{operation} {path}[/]")


# ── Animated thinking spinner ───────────────────────────────────────────────

def _spinner_thread(stop_event, label):
    """Background thread: animate a ghost spinner until stop_event is set."""
    global _spinner_running
    with _spinner_lock:
        _spinner_running = True
    idx = 0
    try:
        while not stop_event.is_set():
            if _spinner_paused:
                time.sleep(0.1)
                continue
            frame = get_mini_goat_frame(idx)
            sys.stdout.write(f"\r\033[K  {frame}  {label}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)
    finally:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        with _spinner_lock:
            _spinner_running = False


class thinking:
    """Context manager that shows an animated goat spinner while the agent works.

    Usage:
        with render.thinking("thinking"):
            result = agent.run(...)
    """

    def __init__(self, label: str = "thinking", duration: float = 0.0):
        self.label = label
        self._stop = None
        self._thread = None

    def __enter__(self):
        if not sys.stdout.isatty() or console.is_terminal is False and not sys.stdout.isatty():
            console.print(Text(f"  {self.label}…", style="dim"))
            return self
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=_spinner_thread, args=(self._stop, self.label), daemon=True
        )
        self._thread.start()
        return self

    def __exit__(self, *exc):
        if self._stop is not None:
            self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        return False


# ── Permission prompt ───────────────────────────────────────────────────────

def confirm_prompt(message: str) -> str:
    """Ask the user y/N/always with a clean styled prompt."""
    global _spinner_paused
    _spinner_paused = True
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    console.print(f"  [bold color(222)]⚠ {message}[/]")
    rendered = Text("  Allow? ", style="color(245)")
    rendered.append("(y)es", style="bold color(114)")
    rendered.append(" / ", style="color(245)")
    rendered.append("(N)o", style="bold color(203)")
    rendered.append(" / ", style="color(245)")
    rendered.append("(a)lways", style="bold color(117)")
    rendered.append(": ", style="color(245)")
    console.print(rendered, end="")
    answer = console.input().strip().lower()
    _spinner_paused = False
    if answer in ("y", "yes"):
        return "allow"
    if answer in ("a", "always"):
        return "always"
    return "deny"


# ── Token-usage rendering ───────────────────────────────────────────────────

def _fmt_tokens(n: int) -> str:
    """Compact thousands grouping for token counts (e.g. 1,234)."""
    return f"{int(n):,}"


def render_token_usage_local(turn_in: int, turn_out: int) -> None:
    """Print a tiny per-turn token line for the interactive chat.

    Shown after each assistant reply so the user can watch context fill up
    without leaving the REPL.
    """
    t = Text("  ✦ ", style="color(147)")
    t.append("tokens")
    t.append(f"  {_fmt_tokens(turn_in)} in", style="color(153)")
    t.append(" / ", style="dim")
    t.append(f"{_fmt_tokens(turn_out)} out", style="color(222)")
    console.print(t, highlight=False)


def render_token_usage_running(turn_in: int, turn_out: int,
                               total_in: int, total_out: int) -> None:
    """Per-turn usage with a running session total, used by the chat REPL."""
    t = Text("  ✦ ", style="color(147)")
    t.append("this turn ", style="dim")
    t.append(f"{_fmt_tokens(turn_in)} in", style="color(153)")
    t.append(" / ", style="dim")
    t.append(f"{_fmt_tokens(turn_out)} out", style="color(222)")
    t.append("   ·   session ", style="dim")
    t.append(f"{_fmt_tokens(total_in)} in", style="color(153)")
    t.append(" / ", style="dim")
    t.append(f"{_fmt_tokens(total_out)} out", style="color(222)")
    console.print(t, highlight=False)


def render_session_token_footer(total_in: int, total_out: int) -> None:
    """Final goodbye shows total tokens for the chat session."""
    t = Text("  ✦ ", style="color(147)")
    t.append("session total ", style="dim")
    t.append(f"{_fmt_tokens(total_in)} in", style="color(153)")
    t.append(" / ", style="dim")
    t.append(f"{_fmt_tokens(total_out)} out", style="color(222)")
    console.print(t, highlight=False)


# ── Streaming indicators ───────────────────────────────────────────────

def render_streaming_tool(name: str, args: dict | None = None) -> None:
    """Show a live tool execution indicator with animated dot."""
    label = name
    if args and isinstance(args, dict):
        path = args.get("path", args.get("file", ""))
        if path:
            label = f"{name} {path}"
    console.print(f"  \u25cf [bold color(117)]{label}[/]")


def render_streaming_tool_done(name: str, result: str = "") -> None:
    """Mark a tool call as complete."""
    brief = ""
    if result:
        brief = " ".join(result.split())[:60]
    tail = f" \u2014 {brief}" if brief else ""
    console.print(f"  \u2713 [dim]{name}{tail}[/]")


def render_streaming_done() -> None:
    """Show completion indicator after streaming finishes."""
    console.print(f"  \u2713 [bold color(114)]Done[/]")


# ── Plan confirmation ──────────────────────────────────────────────────

def confirm_plan(plan: dict) -> str:
    """Display a plan and ask for confirmation. Returns 'yes', 'no', or 'skip'."""
    goal = plan.get("goal", "")
    steps = plan.get("steps", [])
    touches = plan.get("files_touched", [])

    console.print(f"\n  [bold color(147)]Plan: {goal}[/]")
    console.print(f"  [dim]{chr(9472) * 40}[/]")

    for step in steps:
        action = step.get("action", "?")
        desc = step.get("description", "")
        file = step.get("file", "")
        console.print(f"  {step.get('order', 1)}. [bold]{action}[/]  {desc}")
        if file:
            console.print(f"     \u2192 [dim]{file}[/]")

    if touches:
        console.print(f"\n  [dim]Files: {', '.join(touches)}[/]")

    edits = plan.get("estimated_edits", 0)
    console.print(f"  [dim]Estimated edits: {edits}[/]")
    console.print(f"  [dim]{chr(9472) * 40}[/]")
    console.print("  [bold color(114)]Apply plan?[/]  (Y)es / (N)o / (S)kip planning: ", end="")
    try:
        ans = console.input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans in ("y", "yes"):
        return "yes"
    if ans in ("s", "skip"):
        return "skip"
    return "no"


# ── Syntax-highlighted Markdown ────────────────────────────────────────

def render_markdown(text: str) -> None:
    """Render markdown text with syntax highlighting for code blocks."""
    from rich.markdown import Markdown
    md = Markdown(text, code_theme="monokai", inline_code_lexer="python")
    console.print(md)


# ── File blocks ────────────────────────────────────────────────────────

def render_file_block(path: str, content: str, lexer: str | None = None) -> None:
    """Render a file with a header showing the path."""
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich import box

    if lexer is None:
        ext = path.rsplit(".", 1)[-1] if "." in path else "python"
        lexer_map = {"py": "python", "js": "javascript", "ts": "typescript",
                     "rs": "rust", "go": "go", "java": "java", "md": "markdown",
                     "json": "json", "yaml": "yaml", "toml": "toml",
                     "html": "html", "css": "css", "sh": "bash"}
        lexer = lexer_map.get(ext, "python")
    syntax = Syntax(content, lexer, theme="monokai", word_wrap=True, line_numbers=True)
    console.print(Panel(
        syntax,
        title=f"  {path}  ",
        border_style="color(147)",
        box=box.ROUNDED,
        padding=(0, 1),
    ))


# ── Better tables ──────────────────────────────────────────────────────

def render_table(headers: list[str], rows: list[list[str]]) -> None:
    """Render a clean table with headers and rows."""
    from rich.table import Table
    from rich import box

    table = Table(box=box.SIMPLE_HEAD, border_style="dim", header_style="bold color(147)")
    for h in headers:
        table.add_column(h)
    for row in rows:
        table.add_row(*row)
    console.print(table)


# ── Prompt input ───────────────────────────────────────────────────────

def render_colored_prompt() -> None:
    """Print the 'loom > ' prompt with styling."""
    from rich.text import Text
    t = Text("loom > ", style="bold #a78bfa")
    console.print(t, end="")
