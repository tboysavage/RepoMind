from __future__ import annotations

from pathlib import Path

import pytest

from repo_surgeon import fs


def test_iter_files_skips_hidden_and_excluded(tmp_path: Path) -> None:
    (tmp_path / "visible.py").write_text("print('hi')\n")
    (tmp_path / "hidden.txt").write_text("secret")
    (tmp_path / ".hidden.py").write_text("x")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text("pass\n")
    (tmp_path / "__pycache__").mkdir()

    files = list(fs.iter_files(tmp_path, patterns=["*.py"]))
    assert files == [Path("pkg/module.py"), Path("visible.py")]


def test_iter_files_errors_when_not_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    with pytest.raises(NotADirectoryError):
        list(fs.iter_files(file_path))


def test_read_text_handles_encoding(tmp_path: Path) -> None:
    path = tmp_path / "text.txt"
    path.write_bytes("héllo".encode("latin-1"))
    assert fs.read_text(path).startswith("hé")


def test_is_binary(tmp_path: Path) -> None:
    text_file = tmp_path / "text.txt"
    text_file.write_text("hello")
    binary_file = tmp_path / "bin.bin"
    binary_file.write_bytes(b"\x00\x01\x02")
    assert not fs.is_binary(text_file)
    assert fs.is_binary(binary_file)
