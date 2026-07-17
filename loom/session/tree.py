"""Project awareness: build a .gitignore-aware project tree."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _load_gitignore(root: Path) -> set[str]:
    ignored: set[str] = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    gi = root / ".gitignore"
    if gi.exists():
        for line in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ignored.add(line.rstrip("/").split("/")[-1])
    return ignored


def project_tree(root: str | None = None, max_entries: int = 200) -> str:
    """Walk the working dir once and produce a compact tree string."""
    base = Path(root) if root else Path.cwd()
    ignored = _load_gitignore(base)
    # Use `git ls-files` when available for an accurate tracked view.
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            lines = proc.stdout.splitlines()[:max_entries]
            return "\n".join(lines)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    entries: list[str] = []
    for p in sorted(base.rglob("*")):
        if any(part in ignored for part in p.relative_to(base).parts):
            continue
        if p.is_file():
            entries.append(str(p.relative_to(base)))
        if len(entries) >= max_entries:
            break
    return "\n".join(entries)
