"""Safe project-local file and artifact access for the browser client."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

_SENSITIVE_NAMES = {
    ".env",
    ".netrc",
    ".cdsapirc",
    "secrets.yaml",
    "secrets.yml",
    "keys.json",
}
_SKIP_DIRS = {".aero", ".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
_MAX_TEXT_BYTES = 4 * 1024 * 1024


class ArtifactAccessError(ValueError):
    pass


class ArtifactService:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()

    def _relative(self, value: str) -> Path:
        relative = Path(value or ".")
        if relative.is_absolute() or ".." in relative.parts:
            raise ArtifactAccessError("只允许访问当前项目目录中的相对路径")
        candidate = (self.project_dir / relative).resolve()
        try:
            candidate.relative_to(self.project_dir)
        except ValueError as exc:
            raise ArtifactAccessError("路径超出当前项目目录") from exc
        if any(part in _SKIP_DIRS for part in candidate.relative_to(self.project_dir).parts):
            raise ArtifactAccessError("该目录不允许从 Web UI 访问")
        if candidate.name in _SENSITIVE_NAMES:
            raise ArtifactAccessError("敏感文件不允许从 Web UI 访问")
        if candidate.is_symlink():
            raise ArtifactAccessError("符号链接不允许从 Web UI 访问")
        return candidate

    def encode_id(self, value: str) -> str:
        self._relative(value)
        return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")

    def decode_id(self, artifact_id: str) -> Path:
        padded = artifact_id + "=" * (-len(artifact_id) % 4)
        try:
            value = base64.urlsafe_b64decode(padded.encode()).decode()
        except Exception as exc:
            raise ArtifactAccessError("无效的产物 ID") from exc
        return self._relative(value)

    def tree(self, value: str = ".") -> list[dict[str, Any]]:
        directory = self._relative(value)
        if not directory.is_dir():
            raise ArtifactAccessError("目录不存在")
        items: list[dict[str, Any]] = []
        for child in sorted(
            directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())
        ):
            if child.name in _SKIP_DIRS or child.name in _SENSITIVE_NAMES or child.is_symlink():
                continue
            relative = child.relative_to(self.project_dir).as_posix()
            items.append(
                {
                    "name": child.name,
                    "path": relative,
                    "kind": "directory" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                    "artifact_id": self.encode_id(relative) if child.is_file() else None,
                }
            )
        return items

    def metadata(self, artifact_id: str) -> dict[str, Any]:
        path = self.decode_id(artifact_id)
        if not path.is_file():
            raise ArtifactAccessError("产物不存在")
        relative = path.relative_to(self.project_dir).as_posix()
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return {
            "artifact_id": artifact_id,
            "path": relative,
            "name": path.name,
            "size": path.stat().st_size,
            "media_type": media_type,
            "previewable": media_type.startswith(("text/", "image/"))
            or media_type == "application/pdf",
            "mtime_ns": path.stat().st_mtime_ns,
        }

    def path(self, artifact_id: str) -> Path:
        path = self.decode_id(artifact_id)
        if not path.is_file():
            raise ArtifactAccessError("产物不存在")
        return path

    def text(self, artifact_id: str) -> str:
        path = self.path(artifact_id)
        if path.stat().st_size > _MAX_TEXT_BYTES:
            raise ArtifactAccessError("文本文件过大，请下载后查看")
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ArtifactAccessError("该文件不是 UTF-8 文本") from exc
