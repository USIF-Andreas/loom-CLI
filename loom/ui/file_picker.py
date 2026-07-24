"""File picker with fuzzy search — triggered by @ in the chat input.

Supports:
  - @filename  — quick file selection
  - fuzzy search
  - folders
  - multiple files
"""

from __future__ import annotations

from pathlib import Path


def search_files(query: str, workspace: str = ".", max_results: int = 20) -> list[str]:
    root = Path(workspace).resolve()
    results = []
    query_lower = query.lower()

    ignore = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", "target", ".next"}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(p in ignore for p in path.parts):
            continue
        rel = str(path.relative_to(root))
        if query_lower in rel.lower():
            results.append(rel)
        if len(results) >= max_results:
            break

    results.sort(key=lambda p: (
        0 if p.lower().startswith(query_lower) else
        1 if query_lower in p.lower() else 2,
        len(p),
    ))
    return results[:max_results]