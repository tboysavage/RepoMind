"""Filesystem helpers used by Repo-Surgeon."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterator, Optional, Sequence

DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__", ".hg", ".svn"}
DEFAULT_EXCLUDED_FILES = {".DS_Store"}


def ensure_path(path: Path | str) -> Path:
    """Coerce *path* to :class:`~pathlib.Path` and resolve symlinks."""

    return Path(path).expanduser().resolve()


def iter_files(
    root: Path | str,
    *,
    patterns: Optional[Sequence[str]] = None,
    include_hidden: bool = False,
    follow_symlinks: bool = False,
    relative: bool = True,
    exclude_dirs: Optional[Sequence[str]] = None,
    exclude_files: Optional[Sequence[str]] = None,
) -> Iterator[Path]:
    """Yield files contained in *root*.

    Parameters
    ----------
    root:
        Directory to walk.
    patterns:
        Optional glob patterns. When provided, only files matching one of the
        patterns are yielded.
    include_hidden:
        Include files/directories whose name starts with ``.``.
    follow_symlinks:
        Whether to follow symbolic links to directories.
    relative:
        If ``True`` (default) return paths relative to ``root``.
    exclude_dirs / exclude_files:
        Explicit names to skip in addition to :data:`DEFAULT_EXCLUDED_DIRS` and
        :data:`DEFAULT_EXCLUDED_FILES` respectively.
    """

    root_path = ensure_path(root)
    if not root_path.is_dir():
        raise NotADirectoryError(root)

    patterns = tuple(patterns or ())
    exclude_dir_set = DEFAULT_EXCLUDED_DIRS | set(exclude_dirs or ())
    exclude_file_set = DEFAULT_EXCLUDED_FILES | set(exclude_files or ())

    def _walk(directory: Path) -> Iterator[Path]:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name):
            if entry.name.startswith(".") and not include_hidden:
                continue
            if entry.is_dir():
                if entry.name in exclude_dir_set:
                    continue
                if entry.is_symlink() and not follow_symlinks:
                    continue
                yield from _walk(entry)
                continue
            if entry.name in exclude_file_set:
                continue
            if patterns and not any(
                fnmatch.fnmatch(entry.name, pattern) for pattern in patterns
            ):
                continue
            yield entry

    for file_path in _walk(root_path):
        yield file_path.relative_to(root_path) if relative else file_path


def read_text(path: Path | str, *, encoding: str = "utf-8") -> str:
    """Read *path* returning text, tolerating encoding issues."""

    path_obj = Path(path)
    data = path_obj.read_bytes()
    tried = []
    for candidate in [encoding, "utf-8", "latin-1"]:
        if candidate in tried:
            continue
        tried.append(candidate)
        try:
            return data.decode(candidate)
        except UnicodeDecodeError:
            continue
    return data.decode(encoding, errors="replace")


def is_binary(path: Path | str, *, blocksize: int = 1024) -> bool:
    """Heuristic binary file detection."""

    path_obj = Path(path)
    with path_obj.open("rb") as fp:
        chunk = fp.read(blocksize)
    if b"\0" in chunk:
        return True
    text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
    return bool(chunk.translate(None, text_characters))
