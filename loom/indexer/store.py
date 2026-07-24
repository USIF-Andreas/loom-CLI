"""SQLite storage for indexed workspace data."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone

_local = threading.local()


def _get_db(db_path: Path) -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return _local.conn


DB_PATH = Path.home() / ".loom" / "index.db"


def init_store() -> None:
    conn = _get_db(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            language TEXT,
            size INTEGER,
            modified REAL,
            indexed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            name TEXT,
            kind TEXT,
            line INTEGER,
            parent TEXT,
            FOREIGN KEY (file_path) REFERENCES files(path)
        );
        CREATE TABLE IF NOT EXISTS imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            source TEXT,
            target TEXT,
            FOREIGN KEY (file_path) REFERENCES files(path)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            content TEXT,
            line INTEGER,
            FOREIGN KEY (file_path) REFERENCES files(path)
        );
    """)
    conn.commit()


def clear_index() -> None:
    conn = _get_db(DB_PATH)
    conn.executescript("DELETE FROM files; DELETE FROM symbols; DELETE FROM imports; DELETE FROM comments;")
    conn.commit()


def save_file(path: str, language: str, size: int, modified: float) -> None:
    conn = _get_db(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO files (path, language, size, modified, indexed_at) VALUES (?, ?, ?, ?, ?)",
        (path, language, size, modified, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def save_symbol(file_path: str, name: str, kind: str, line: int, parent: str = "") -> None:
    conn = _get_db(DB_PATH)
    conn.execute(
        "INSERT INTO symbols (file_path, name, kind, line, parent) VALUES (?, ?, ?, ?, ?)",
        (file_path, name, kind, line, parent),
    )
    conn.commit()


def save_import(file_path: str, source: str, target: str) -> None:
    conn = _get_db(DB_PATH)
    conn.execute(
        "INSERT INTO imports (file_path, source, target) VALUES (?, ?, ?)",
        (file_path, source, target),
    )
    conn.commit()


def save_comment(file_path: str, content: str, line: int) -> None:
    conn = _get_db(DB_PATH)
    conn.execute(
        "INSERT INTO comments (file_path, content, line) VALUES (?, ?, ?)",
        (file_path, content, line),
    )
    conn.commit()


def get_stats() -> dict:
    conn = _get_db(DB_PATH)
    files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0] or 0
    symbols = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] or 0
    imports = conn.execute("SELECT COUNT(*) FROM imports").fetchone()[0] or 0
    return {"files": files, "symbols": symbols, "imports": imports}


def get_files_by_language() -> dict[str, int]:
    conn = _get_db(DB_PATH)
    rows = conn.execute("SELECT language, COUNT(*) FROM files GROUP BY language").fetchall()
    return {r[0]: r[1] for r in rows}


def search_symbols(query: str) -> list[dict]:
    conn = _get_db(DB_PATH)
    rows = conn.execute(
        "SELECT file_path, name, kind, line FROM symbols WHERE name LIKE ? LIMIT 50",
        (f"%{query}%",),
    ).fetchall()
    return [{"file": r[0], "name": r[1], "kind": r[2], "line": r[3]} for r in rows]


def get_file_imports(file_path: str) -> list[str]:
    conn = _get_db(DB_PATH)
    rows = conn.execute(
        "SELECT target FROM imports WHERE file_path = ? OR source = ?",
        (file_path, file_path),
    ).fetchall()
    return [r[0] for r in rows]
