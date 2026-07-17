"""Search tools: glob and grep."""

from __future__ import annotations

import subprocess
from pathlib import Path


def glob(pattern: str, root: str | None = None) -> list[str]:
    """Return a list of paths matching the glob pattern."""
    base = Path(root) if root else Path.cwd()
    results = [str(p) for p in sorted(base.glob(pattern))]
    return results


def grep(pattern: str, path: str | None = None, ignore_case: bool = False) -> list[str]:
    """Search file contents for a pattern.

    Uses ripgrep if available, otherwise falls back to a Python search.
    Returns a list of formatted match lines.
    """
    target = path or "."
    try:
        cmd = ["rg", "--line-number", "--with-filename"]
        if ignore_case:
            cmd.append("-i")
        cmd += ["--", pattern, target]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return proc.stdout.splitlines()
        if proc.returncode == 1:
            return []  # no matches
        # rg error (e.g. bad pattern) — fall through to python
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return _python_grep(pattern, target, ignore_case)


def _python_grep(pattern: str, target: str, ignore_case: bool) -> list[str]:
    import re

    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)
    root = Path(target)
    paths = [root] if root.is_file() else list(root.rglob("*"))
    matches: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                matches.append(f"{p}:{i}:{line}")
    return matches
