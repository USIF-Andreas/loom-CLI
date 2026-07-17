"""Colorful ASCII-art logo for loom, plus a small animation helper.

The logo is rendered with a per-line rainbow gradient using rich. A tiny
spinner utility is provided for "thinking"/"working" states in the chat loop.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

console = Console()

# Plain banner (used for tests / non-tty fallback).
LOOM_LOGO_BLOCK = r"""
██╗      ██████╗  ██████╗ ███╗   ███╗
██║     ██╔═══██╗██╔═══██╗████╗ ████║
██║     ██║   ██║██║   ██║██╔████╔██║
██║     ██║   ██║██║   ██║██║╚██╔╝██║
███████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║
╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝
 ✦ a terminal agentic coding assistant
"""

# A wider, more "modern" banner variant (slant font style).
LOOM_LOGO_WIDE = r"""
 _                _
| |              | |
| | ___   ___   _| |__   __ _ _ __ _ __ __ _ _ __ ___
| |/ / | | \ \ / / '_ \ / _` | '__| '__/ _` | '__/ _ \
|   <| |_| |\ V /| | | | (_| | |  | | | (_| | | |  __/
|_|\_\\__, | \_/ |_| |_|\__,_|_|  |_|  \__,_|_|  \___|
      __/ |
     |___/
 a terminal agentic coding assistant
"""

# Rainbow gradient stops (rich color names) cycled per line.
RAINBOW = [
    "bold bright_cyan",
    "bold bright_blue",
    "bold magenta",
    "bold bright_magenta",
    "bold bright_yellow",
    "bold bright_green",
    "bold bright_red",
]


def render_logo(use_wide: bool = False) -> None:
    """Print the loom banner with a per-line rainbow gradient.

    Falls back to plain text when output is not a TTY (e.g. piped / tests).
    """
    banner = LOOM_LOGO_WIDE if use_wide else LOOM_LOGO_BLOCK
    lines = [ln for ln in banner.split("\n")]
    if not console.is_terminal:
        console.print(banner)
        return
    for i, line in enumerate(lines):
        style = RAINBOW[i % len(RAINBOW)]
        console.print(Text(line, style=style), highlight=False)


def animate_thinking(label: str = "thinking", frames: str | None = None,
                     duration: float = 1.2) -> None:
    """Show a brief spinner animation, then erase it.

    Used to give visual feedback that the agent is working (e.g. before a
    stream starts). Sleeps for ``duration`` seconds while animating.
    """
    if frames is None:
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    if not console.is_terminal:
        console.print(Text(f"{label}…", style="dim"))
        return
    import time

    end = time.time() + duration
    idx = 0
    try:
        while time.time() < end:
            frame = frames[idx % len(frames)]
            console.print(
                Text(f"\r{frame} {label}…", style="bold bright_magenta"),
                end="",
            )
            time.sleep(0.08)
            idx += 1
        # Clear the spinner line.
        console.print(
            Text("\r" + " " * (len(label) + 4), style="bold bright_magenta"),
            end="",
        )
        console.print()
    except KeyboardInterrupt:
        console.print()
