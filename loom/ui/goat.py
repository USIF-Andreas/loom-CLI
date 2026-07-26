"""ASCII ghost animation with color gradient — clean, readable, animated."""

from __future__ import annotations

import sys
import time

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

GHOST_COLOR = "#8860b8"

FRAME_FORWARD = """   ▐   ▐
 ▄███████▄
██  ▐ ▐  ██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""

FRAME_LEFT = """   ▐   ▐
 ▄███████▄
██ ▐ ▐   ██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""

FRAME_RIGHT = """   ▐   ▐
 ▄███████▄
██   ▐ ▐ ██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""

FRAME_BLINK = """   ▐   ▐
 ▄███████▄
██▄▄█▄█▄▄██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""

FRAME_WINK = """   ▐   ▐
 ▄███████▄
██▄▄█ ▐  ██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""

FLY_FRAMES = [FRAME_FORWARD, FRAME_LEFT, FRAME_FORWARD, FRAME_RIGHT, FRAME_FORWARD, FRAME_BLINK, FRAME_FORWARD, FRAME_WINK, FRAME_FORWARD, FRAME_BLINK, FRAME_FORWARD]

_ALT_FRAMES = [FRAME_FORWARD, FRAME_LEFT, FRAME_RIGHT, FRAME_BLINK, FRAME_WINK]

ANIMATIONS = {
    "fly": FLY_FRAMES,
    "float": FLY_FRAMES,
    "glide": FLY_FRAMES,
    "idle": FLY_FRAMES,
    "walk": FLY_FRAMES,
    "think": FLY_FRAMES,
    "dance": FLY_FRAMES,
    "jump": FLY_FRAMES,
}

SEQUENCE = [
    (FRAME_FORWARD, 1.5),
    (FRAME_LEFT, 0.6),
    (FRAME_FORWARD, 0.8),
    (FRAME_RIGHT, 0.6),
    (FRAME_FORWARD, 1.0),
    (FRAME_BLINK, 0.15),
    (FRAME_FORWARD, 1.2),
    (FRAME_WINK, 0.4),
    (FRAME_FORWARD, 0.2),
    (FRAME_BLINK, 0.15),
]


def _color_frame(frame: str, color: str = GHOST_COLOR) -> Text:
    text = Text()
    for line in frame.strip("\n").split("\n"):
        for ch in line:
            if ch == "█":
                text.append("█", style=f"bold {color}")
            elif ch == "▄":
                text.append("▄", style=color)
            elif ch == "▀":
                text.append("▀", style=f"dim {color}")
            elif ch == "▐":
                text.append("▐", style=f"bold #ffe066")
            else:
                text.append(ch, style=color)
        text.append("\n")
    return text


# ── Single-line spinner ─────────────────────────────────────────────────

_SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def get_mini_goat_frame(idx: int) -> str:
    spinner = _SPINNER_CHARS[idx % len(_SPINNER_CHARS)]
    return f"{spinner} 👻"


# ── Banner ──────────────────────────────────────────────────────────────

def render_goat_banner() -> None:
    content = _color_frame(FRAME_FORWARD)
    panel = Panel(
        content,
        box=box.ROUNDED,
        border_style=GHOST_COLOR,
        padding=(0, 2),
        expand=False,
    )
    console.print(panel)


# ── Animation ───────────────────────────────────────────────────────────

def animate_goat_terminal(
    animation_name: str = "fly",
    loops: int = 5,
    delay: float = 0.18,
    title: str = "",
) -> None:
    if not sys.stdout.isatty():
        console.print(f"[dim][ghost: {animation_name}][/]")
        return

    frames = ANIMATIONS.get(animation_name, FLY_FRAMES)
    frame_height = 6

    if title:
        console.print(f"  [{GHOST_COLOR}]{title}[/]")

    for _ in range(frame_height):
        sys.stdout.write("\n")

    try:
        for _ in range(loops):
            for frame in frames:
                sys.stdout.write(f"\033[{frame_height}A\033[J")
                sys.stdout.flush()
                console.print(_color_frame(frame))
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    console.print()


def animate_goat_walk_across(steps: int = 16, delay: float = 0.07) -> None:
    if not sys.stdout.isatty():
        console.print("[dim][ghost walked across][/]")
        return

    frames = _ALT_FRAMES
    frame_height = 6

    for _ in range(frame_height):
        sys.stdout.write("\n")

    try:
        for step in range(steps):
            frame = frames[step % len(frames)]
            sys.stdout.write(f"\033[{frame_height}A\033[J")
            sys.stdout.flush()
            padding = " " * min(step * 2, 48)
            content = _color_frame(frame)
            for line in content.split("\n"):
                console.print(f"  {padding}{line}")
            time.sleep(delay)
    except KeyboardInterrupt:
        pass
    console.print(f"  [{GHOST_COLOR} dim]the ghost floated away…[/]")


# ── Original sequential animation ───────────────────────────────────────

def animate_sequence(title: str = "") -> None:
    if not sys.stdout.isatty():
        console.print("[dim][ghost sequence][/]")
        return

    console.print(f"\033[?25l", end="")
    print("\n" * 5)

    try:
        while True:
            for frame, duration in SEQUENCE:
                sys.stdout.write("\033[6A\033[J")
                sys.stdout.write(_color_frame(frame).plain.replace("\n", "\n") + "\n")
                sys.stdout.flush()
                time.sleep(duration)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\n")


# ── Slash command ────────────────────────────────────────────────────────

_SHOW_CONFIG = {
    "fly":   ("fly",   6, 0.18, "👻 ghost flying…"),
    "float": ("fly",   6, 0.25, "👻 ghost floating…"),
    "glide": ("fly",   6, 0.15, "👻 ghost gliding…"),
    "idle":  ("fly",   6, 0.18, "👻 ghost hovering…"),
    "walk":  ("fly",   6, 0.18, "👻 ghost flying…"),
    "think": ("fly",   6, 0.22, "👻 ghost pondering…"),
    "dance": ("fly",   8, 0.10, "👻 ghost dancing!"),
    "jump":  ("fly",   6, 0.09, "👻 ghost soaring!"),
}


def play_goat_show(action: str = "all") -> None:
    action = (action or "all").lower().strip()

    if action in ("fly_across", "walk_across", "walk2"):
        animate_goat_walk_across(steps=18, delay=0.06)
        return

    if action in _SHOW_CONFIG:
        name, loops, delay, title = _SHOW_CONFIG[action]
        animate_goat_terminal(name, loops, delay, title)
        return

    console.print(f"\n  [bold {GHOST_COLOR}]✦ ghost showcase ✦[/]\n")
    for key in ("fly", "float", "dance"):
        name, loops, delay, title = _SHOW_CONFIG[key]
        animate_goat_terminal(name, min(loops, 3), delay, title)
    animate_goat_walk_across(steps=12, delay=0.05)
    console.print(f"  [{GHOST_COLOR}]✦ show complete ✦[/]\n")
