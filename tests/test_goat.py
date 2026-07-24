"""Tests for loom pixel goat animations and UI elements."""

from __future__ import annotations

from unittest.mock import patch
from loom.ui import goat


def test_mini_goat_frame_cycle():
    frame1 = goat.get_mini_goat_frame(0)
    frame2 = goat.get_mini_goat_frame(1)
    assert "(" in frame1 or "⠋" in frame1
    assert frame1 != frame2


def test_goat_animations_dict():
    assert "walk" in goat.ANIMATIONS
    assert "idle" in goat.ANIMATIONS
    assert "think" in goat.ANIMATIONS
    assert "dance" in goat.ANIMATIONS
    assert "jump" in goat.ANIMATIONS
    for key, frames in goat.ANIMATIONS.items():
        assert len(frames) > 0
        assert len(frames[0]) >= 2


def test_goat_non_tty_animation():
    with patch("sys.stdout.isatty", return_value=False):
        # Should execute safely without raising terminal escape code errors
        goat.animate_goat_terminal("walk", loops=1, delay=0.01)
        goat.animate_goat_walk_across(steps=2, delay=0.01)
        goat.render_goat_banner()


def test_goat_slash_command_execution():
    with patch("sys.stdout.isatty", return_value=False):
        goat.play_goat_show("idle")
        goat.play_goat_show("dance")
