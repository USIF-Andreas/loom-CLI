"""Unit tests for file tools."""

from __future__ import annotations

from loom.tools import files


def test_read_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world")
    assert files.read_file(str(f)) == "hello world"


def test_read_missing(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        files.read_file(str(tmp_path / "nope.txt"))


def test_write_file_creates_parents(tmp_path):
    target = tmp_path / "sub" / "b.txt"
    res = files.write_file(str(target), "data")
    assert target.read_text() == "data"
    assert "Wrote" in res


def test_edit_file_unique(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("foo bar baz")
    res = files.edit_file(str(f), "bar", "QUX")
    assert "Edited" in res
    assert f.read_text() == "foo QUX baz"


def test_edit_file_not_found(tmp_path):
    import pytest

    f = tmp_path / "d.txt"
    f.write_text("abc")
    with pytest.raises(ValueError):
        files.edit_file(str(f), "zzz", "yyy")


def test_edit_file_ambiguous(tmp_path):
    import pytest

    f = tmp_path / "e.txt"
    f.write_text("x x x")
    with pytest.raises(ValueError):
        files.edit_file(str(f), "x", "y")
