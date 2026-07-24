"""Interactive Diff — shows diffs and asks accept/reject/edit before applying edits."""

from __future__ import annotations

import difflib
from pathlib import Path


def generate_diff(original: str, modified: str, file_path: str = "") -> str:
    """Generate a unified diff string between original and modified content."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines, mod_lines,
        fromfile=f"a/{file_path}" if file_path else "a",
        tofile=f"b/{file_path}" if file_path else "b",
        n=3,
    )
    return "".join(diff)


def apply_diff(file_path: str, diff_text: str) -> str:
    """Apply a unified diff to a file. Returns result or error message."""
    import subprocess
    try:
        proc = subprocess.run(
            ["patch", "-u", file_path],
            input=diff_text,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return f"Applied diff to {file_path}"
        return f"Patch failed: {proc.stderr or proc.stdout}"
    except Exception as exc:
        return f"Error applying diff: {exc}"
