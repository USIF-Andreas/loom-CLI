"""Enhanced animated startup logo with LOGO text and ASCII goat animation."""

from __future__ import annotations

import sys
import time

from rich.console import Console
from rich.text import Text

console = Console()

# ASCII Art for LOGO
LOGO_SMALL = r"""
  ____            _     ____
 |  _ \ ___  __ _| |_  / ___|___  _ __ ___
 | |_) / _ \/ _` | __| | __/ _ \| '_ ` _ \
 |  _ <  __/ (_| | |_  | | (_) | | | | | |
 |_| \_\___|\__,_|\__|  \____\___/|_| |_|_|
"""

LOGO_LARGE = r"""
  ____               _ _           _
 |  _ \ __ _ _ __ __| | |__   ___ | |_ ___
 | |_) / _` | '__/ _` | '_ \ / _ \| __/ __|
 |  __/ (_| | | | (_| | | | | (_) | |_ \__ \
 |_|  \__,_|_|  \__,_|_| |_|\___/ \__|___/
"""

# Goat frames from the original animation (combining user's provided frames with existing ones)
GOAT_FRAMES = {
    "forward": r"""   ▐   ▐
 ▄███████▄
██  ▐ ▐  ██
██       ██
 ▀███████▀
  ▄▀   ▀▄""",

    "left": r"""   ▐   ▐
 ▄███████▄
██ ▐ ▐   ██
██       ██
 ▀███████▀
  ▄▀   ▀▄""",

    "right": r"""   ▐   ▐
 ▄███████▄
██   ▐ ▐ ██
██       ██
 ▀███████▀
  ▄▀   ▀▄""",

    "blink": r"""   ▐   ▐
 ▄███████▄
██▄▄█▄█▄▄██
██       ██
 ▀███████▀
  ▄▀   ▀▄""",

    "wink": r"""   ▐   ▐
 ▄███████▄
██▄▄█ ▐  ██
██       ██
 ▀███████▀
  ▄▀   ▀▄"""
}

# Animation sequence combining movement with facial expressions
ANIMATION_SEQUENCE = [
    ("forward", 1.5),
    ("left", 0.6),
    ("forward", 0.8),
    ("right", 0.6),
    ("forward", 1.0),
    ("blink", 0.15),
    ("forward", 1.2),
    ("wink", 0.4),
    ("forward", 0.2),
    ("blink", 0.15),
]

def render_logo(use_wide: bool = False, show_goat: bool = True, show_text: bool = True) -> None:
    """Render the enhanced logo with optional goat animation and text."""
    if not show_goat and not show_text:
        return

    if not console.is_terminal:
        if show_text:
            console.print(LOGO_SMALL.strip("\n"))
        if show_goat:
            console.print(GOAT_FRAMES["forward"].strip("\n"))
        console.print()
        return

    _animate_enhanced_logo(show_goat, show_text, use_wide)

def _animate_enhanced_logo(show_goat: bool, show_text: bool, use_wide: bool) -> None:
    """Animate the combined logo with goat and text."""
    # Clear screen and hide cursor
    sys.stdout.write("\033[3J\033[2J\033[H")
    sys.stdout.flush()
    time.sleep(0.1)

    # Hide cursor for smoother animation
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        # Animate through the sequence
        for frame_name, duration in ANIMATION_SEQUENCE:
            # Clear screen and move cursor to home
            sys.stdout.write("\033[H\033[J")
            sys.stdout.flush()

            # Build the display content
            lines = []

            if show_text:
                # Add logo text (using small version for animation to reduce flicker)
                logo_lines = LOGO_SMALL.strip("\n").split("\n")
                # Add some spacing above the logo
                lines.extend([""] * 2)
                lines.extend(logo_lines)
                lines.append("")  # Space between logo and goat

            if show_goat:
                # Add the goat frame
                goat_lines = GOAT_FRAMES[frame_name].strip("\n").split("\n")
                lines.extend(goat_lines)

            # Print the combined output
            if lines:
                # Center the content
                max_width = max(len(line) for line in lines if line) if any(line.strip() for line in lines) else 0
                padded_lines = []
                for line in lines:
                    if line.strip():  # Non-empty line
                        padding = " " * max(0, (max_width - len(line)) // 2)
                        padded_lines.append(padding + line)
                    else:
                        padded_lines.append("")  # Keep empty lines for spacing
                content = "\n".join(padded_lines)
            else:
                content = ""

            # Apply color to the goat (keeping text white/default)
            if show_goat and content:
                lines = content.split("\n")
                colored_lines = []
                for line in lines:
                    if any(char in line for char in ["█", "▄", "▀", "▐"]):  # Goat characters
                        colored_line = ""
                        for char in line:
                            if char == "█":
                                colored_line += "[bold #8860b8]█[/]"
                            elif char == "▄":
                                colored_line += "[#8860b8]▄[/]"
                            elif char == "▀":
                                colored_line += "[dim #8860b8]▀[/]"
                            elif char == "▐":
                                colored_line += "[bold #ffe066]▐[/]"
                            else:
                                colored_line += char
                        colored_lines.append(colored_line)
                    else:
                        colored_lines.append(line)
                content = "\n".join(colored_lines)

            # Print with styling
            if content.strip():
                from rich.console import Console
                console = Console()
                print(f"\n{content}\n")

            # Wait for the specified duration
            time.sleep(duration)

    finally:
        # Show cursor again
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        # Final newline
        print()

def animate_thinking(label: str = "thinking", frames: str | None = None,
                     duration: float = 1.2) -> None:
    """Show thinking animation with mini goat."""
    from .goat import get_mini_goat_frame

    if not console.is_terminal:
        console.print(Text(f"{label}…", style="dim"))
        return

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

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
        )
    except KeyboardInterrupt:
        console.print()
    finally:
        # Show cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
"""