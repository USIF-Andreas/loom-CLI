"""Unit tests for SQLite session persistence."""

from __future__ import annotations

from loom.session import db
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def test_create_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "sessions.db")
    db.init_db()
    sid = "abc123"
    db.create_session(sid, "/work")
    db.save_message(sid, HumanMessage(content="hello"))
    db.save_message(sid, AIMessage(content="hi there"))

    sessions = db.list_sessions()
    assert any(s["id"] == sid for s in sessions)

    msgs = db.load_session_messages(sid)
    assert len(msgs) == 2
    assert isinstance(msgs[0], HumanMessage)
    assert msgs[1].content == "hi there"


def test_tool_message_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "sessions.db")
    db.init_db()
    sid = "t1"
    db.create_session(sid, ".")
    db.save_message(sid, ToolMessage(content="result", tool_call_id="c1"))
    msgs = db.load_session_messages(sid)
    assert msgs[0].content == "result"
