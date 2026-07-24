"""Animated startup logo — animated ASCII ghost."""

from __future__ import annotations

import sys
import time

from rich.console import Console
from rich.text import Text

console = Console()

GOAT_SMALL = r"""
      ▐   ▐
    ▄███████▄
   ██  ▐ ▐  ██
   ██       ██
    ▀███████▀
     ▄▀   ▀▄
"""


def render_logo(use_wide: bool = False, show_goat: bool = True) -> None:
    if not show_goat:
        return
    if not console.is_terminal:
        console.print(GOAT_SMALL.strip("\n"))
        console.print()
        return
    _animate_ghost()


def _animate_ghost() -> None:
    from .goat import _color_frame, FLY_FRAMES

    sys.stdout.write("\033[3J\033[2J\033[H")
    sys.stdout.flush()
    time.sleep(0.15)

    for frame in FLY_FRAMES:
        sys.stdout.write("\033[H\033[J")
        sys.stdout.flush()
        console.print(_color_frame(frame))
        time.sleep(0.12)
    console.print()


def animate_thinking(label: str = "thinking", frames: str | None = None,
                     duration: float = 1.2) -> None:
    from .goat import get_mini_goat_frame

    if not console.is_terminal:
        console.print(Text(f"{label}…", style="dim"))
        return

    end = time.time() + duration
    idx = 0
    try:
        while time.time() < end:
            frame = get_mini_goat_frame(idx)
            console.print(
                Text(f"\r{frame} {label}…", style="#c0c0e0"),
                end="",
            )
            time.sleep(0.08)
            idx += 1
        console.print(
            "\r" + " " * (len(label) + 30) + "\r",
            end="",
            highlight=False,
        )
    except KeyboardInterrupt:
        console.print()


def animate_status(text: str) -> None:
    """Animate the provider/model status line with a color sweep."""
    if not console.is_terminal:
        console.print(Text(f"  {text}", style="dim"))
        return

    colors = [(124,58,237), (167,139,250), (34,211,238), (103,232,249), (167,139,250), (124,58,237)]
    for i in range(8):
        r, g, b = colors[i % len(colors)]
        sys.stdout.write(f"\r\033[38;2;{r};{g};{b}m  {text}\033[0m")
        sys.stdout.flush()
        time.sleep(0.04)
    sys.stdout.write(f"\r\033[0m  {text}\033[0m\n")
    sys.stdout.flush()
