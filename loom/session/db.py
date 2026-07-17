"""SQLite session persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

DB_PATH = Path.home() / ".loom" / "sessions.db"

_ROLE_MAP = {
    SystemMessage: "system",
    HumanMessage: "user",
    AIMessage: "assistant",
    ToolMessage: "tool",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP,
            working_dir TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            tool_calls TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        """
    )
    conn.commit()
    conn.close()


def create_session(session_id: str, working_dir: str) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, created_at, working_dir) VALUES (?, ?, ?)",
        (session_id, _now(), working_dir),
    )
    conn.commit()
    conn.close()


def save_message(session_id: str, message: BaseMessage) -> None:
    conn = _connect()
    role = _ROLE_MAP.get(type(message), "unknown")
    content = _content_to_str(message)
    tool_calls = json.dumps(
        getattr(message, "tool_calls", None) or [], default=str
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, tool_calls, _now()),
    )
    conn.commit()
    conn.close()


def _content_to_str(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return json.dumps(content, default=str)


def load_session_messages(session_id: str) -> list[BaseMessage]:
    """Reload a session's messages into LangChain message objects."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, tool_calls FROM messages WHERE session_id = ? "
        "ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()

    out: list[BaseMessage] = []
    for role, content, tool_calls in rows:
        out.append(_row_to_message(role, content))
    return out


def _row_to_message(role: str, content: str) -> BaseMessage:
    if role == "system":
        return SystemMessage(content=content)
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    if role == "tool":
        return ToolMessage(content=content, tool_call_id="")
    return HumanMessage(content=content)


def list_sessions() -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT id, created_at, working_dir FROM sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "created_at": r[1], "working_dir": r[2]} for r in rows
    ]
