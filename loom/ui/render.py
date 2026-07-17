"""Rich-based terminal rendering and live permission prompts."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console()

ROLE_COLORS = {
    "user": "bright_green",
    "assistant": "bright_blue",
    "tool_call": "bright_magenta",
    "tool_result": "bright_cyan",
    "system": "dim",
    "error": "bright_red",
}


def render_role(role: str, text: str) -> None:
    color = ROLE_COLORS.get(role, "white")
    console.print(Text(f"[{role}] ", style=f"bold {color}"))


def render_text(role: str, text: str) -> None:
    color = ROLE_COLORS.get(role, "white")
    console.print(Text(text, style=color))


def render_code(content: str, lexer: str = "python") -> None:
    console.print(Syntax(content, lexer, theme="monokai", word_wrap=True))


def render_diff(diff_text: str) -> None:
    console.print(Panel(diff_text, title="diff", border_style="yellow"))


def render_error(msg: str) -> None:
    console.print(Text(msg, style="bold bright_red"))


def confirm_prompt(message: str) -> str:
    """Ask the user y/N/always. Returns 'allow', 'deny', or 'always'."""
    rendered = Text("\n⚠ ", style="bold bright_yellow")
    rendered.append(message + " ", style="bright_yellow")
    rendered.append("Allow? [y/N/always]: ", style="bold")
    console.print(rendered, end="")
    answer = console.input().strip().lower()
    if answer in ("y", "yes"):
        return "allow"
    if answer in ("a", "always"):
        return "always"
    return "deny"
