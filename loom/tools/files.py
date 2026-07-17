"""File system tools: read, write, edit."""

from __future__ import annotations

from pathlib import Path


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def read_file(path: str) -> str:
    """Read a file and return its contents as a string."""
    p = _resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fall back to latin-1 for binary-ish files.
        return p.read_text(encoding="latin-1")


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace an exact string match in a file.

    Raises ValueError if old_str is not found or is not unique.
    """
    if old_str == new_str:
        return "No change: old_str equals new_str"
    text = read_file(path)
    count = text.count(old_str)
    if count == 0:
        raise ValueError(f"old_str not found in {path}")
    if count > 1:
        raise ValueError(
            f"old_str is not unique in {path} ({count} matches). "
            "Provide more surrounding context to disambiguate."
        )
    new_text = text.replace(old_str, new_str, 1)
    write_file(path, new_text)
    return f"Edited {path} ({len(old_str)} -> {len(new_str)} chars)"
