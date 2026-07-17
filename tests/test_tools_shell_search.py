"""Unit tests for shell and search tools."""

from __future__ import annotations

from loom.tools import search, shell


def test_bash_echo():
    out = shell.bash("echo hi")
    assert "hi" in out
    assert "exit_code=0" in out


def test_bash_exit_code():
    out = shell.bash("exit 3")
    assert "exit_code=3" in out


def test_bash_timeout():
    out = shell.bash("sleep 5", timeout=1)
    assert "timed out" in out


def test_glob(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    (tmp_path / "c.txt").write_text("")
    res = search.glob("*.py", root=str(tmp_path))
    assert len(res) == 2


def test_grep(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("def hello():\n    return 1\n")
    res = search.grep("hello", path=str(tmp_path))
    assert any("hello" in line for line in res)


def test_grep_no_match(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x = 1\n")
    assert search.grep("zzzzz", path=str(tmp_path)) == []
