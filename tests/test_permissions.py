"""Unit tests for the permission denylist."""

from __future__ import annotations

from loom.ui import confirm


def test_denylist_rm_root():
    assert confirm.is_denied("rm -rf /") is not None
    assert confirm.is_denied("sudo rm -rf /var") is not None


def test_denylist_fork_bomb():
    assert confirm.is_denied(":(){ :|:& };:") is not None


def test_denylist_not_triggered_on_safe():
    assert confirm.is_denied("rm -rf build/") is None
    assert confirm.is_denied("ls -la") is None


def test_sensitive_detection():
    assert confirm.is_sensitive("rm -rf dist")
    assert not confirm.is_sensitive("ls")
    assert confirm.needs_permission("bash", {"command": "rm -rf x"})
    assert not confirm.needs_permission("read_file", {"path": "y"})
