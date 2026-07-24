"""Workspace Indexer — understands entire projects.

Walks the workspace, identifies files by language, extracts symbols,
imports, classes, functions, and comments. Stores results in SQLite
for fast lookup and smart context selection.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import parsers
from . import store

INDEX_VERSION = 1


def index_workspace(workspace: str = ".") -> dict:
    """Index all supported files in the workspace. Returns summary stats."""
    start = time.time()
    root = Path(workspace).resolve()

    store.init_store()
    store.clear_index()

    file_count = 0
    symbol_count = 0
    import_count = 0
    lang_counts: dict[str, int] = {}

    for path in root.rglob("*"):
        if not path.is_file() or not parsers.should_index(path):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = str(path.relative_to(root))
        ext = path.suffix
        lang = parsers.LANG_MAP.get(ext, "Unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

        stat = path.stat()
        store.save_file(
            path=rel,
            language=lang,
            size=stat.st_size,
            modified=stat.st_mtime,
        )

        parsed = parsers.parse_file(content, str(path))
        for sym in parsed["symbols"]:
            store.save_symbol(rel, sym["name"], sym["kind"], sym["line"], sym["parent"])
            symbol_count += 1
        for imp in parsed["imports"]:
            store.save_import(rel, imp["source"], imp["target"])
            import_count += 1

        file_count += 1

    elapsed = time.time() - start
    return {
        "files": file_count,
        "symbols": symbol_count,
        "imports": import_count,
        "languages": lang_counts,
        "elapsed": round(elapsed, 2),
    }


def index_status() -> dict:
    """Return current index stats without re-indexing."""
    return store.get_stats()


def search(q: str) -> list[dict]:
    """Search indexed symbols."""
    return store.search_symbols(q)


def get_file_dependencies(file_path: str) -> list[str]:
    """Get import dependencies for a file."""
    return store.get_file_imports(file_path)


def languages() -> dict[str, int]:
    """Get file count per language."""
    return store.get_files_by_language()
