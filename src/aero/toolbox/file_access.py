"""Shared state and safety checks for local file tools."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from aero.toolbox.paths import find_workspace_dir

_READ_FILES: ContextVar[set[str] | None] = ContextVar("aero_read_files", default=None)


def _current_read_files() -> set[str]:
    files = _READ_FILES.get()
    if files is None:
        files = set()
        _READ_FILES.set(files)
    return files


class _ContextReadFiles:
    """Set-like compatibility proxy whose contents are scoped to one task."""

    def add(self, value: str) -> None:
        _current_read_files().add(value)

    def clear(self) -> None:
        _current_read_files().clear()

    def __contains__(self, value: object) -> bool:
        return value in _current_read_files()

    def __iter__(self) -> Iterator[str]:
        return iter(_current_read_files())

    def __len__(self) -> int:
        return len(_current_read_files())


READ_FILES = _ContextReadFiles()


@contextmanager
def use_read_files(files: set[str] | None = None):
    token = _READ_FILES.set(files if files is not None else set())
    try:
        yield
    finally:
        _READ_FILES.reset(token)


def is_in_project(path: Path) -> bool:
    project_dir = find_workspace_dir()
    try:
        path.resolve().relative_to(project_dir.resolve())
        return True
    except ValueError:
        return False
