"""Project-scoped research memos persisted as structured JSON."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MEMO_STORE_PATH = Path(".aero") / "memos.json"
MAX_MEMO_CONTEXT_CHARS = 8000


class MemoError(RuntimeError):
    """Raised when a memo operation cannot be completed."""


class MemoStore:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir).resolve()
        self.path = self.project_dir / MEMO_STORE_PATH

    def add(
        self,
        *,
        title: str,
        content: str,
        evidence: str = "",
        tags: list[str] | None = None,
        experiment_id: str | None = None,
        experiment_name: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        title = _clean_required(title, "备忘录标题")
        content = _clean_required(content, "备忘录内容")
        evidence = evidence.strip()
        clean_tags = _clean_tags(tags or [])
        records = self.list()
        duplicate = next(
            (
                item
                for item in records
                if item.get("title") == title and item.get("content") == content
            ),
            None,
        )
        if duplicate is not None:
            return duplicate, False

        now = time.time()
        memo = {
            "id": (
                f"memo-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
                f"{uuid.uuid4().hex[:6]}"
            ),
            "title": title,
            "content": content,
            "evidence": evidence,
            "tags": clean_tags,
            "experiment_id": experiment_id or None,
            "experiment_name": experiment_name or None,
            "created_at": now,
            "updated_at": now,
        }
        records.append(memo)
        self._write(records)
        return memo, True

    def list(self, *, query: str = "", limit: int | None = None) -> list[dict[str, Any]]:
        records = self._read()
        query = query.strip().casefold()
        if query:
            records = [
                item
                for item in records
                if query
                in " ".join(
                    [
                        str(item.get("title", "")),
                        str(item.get("content", "")),
                        str(item.get("evidence", "")),
                        " ".join(item.get("tags", [])),
                    ]
                ).casefold()
            ]
        records.sort(key=lambda item: item.get("created_at", 0), reverse=True)
        return records[:limit] if limit is not None else records

    def delete(self, memo_id: str) -> dict[str, Any]:
        records = self._read()
        memo = self._find_unique(records, memo_id)
        self._write([item for item in records if item is not memo])
        return memo

    def update(
        self,
        memo_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        evidence: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        if all(value is None for value in (title, content, evidence, tags)):
            raise MemoError("没有提供要更新的备忘录内容。")
        records = self._read()
        memo = self._find_unique(records, memo_id)
        if title is not None:
            memo["title"] = _clean_required(title, "备忘录标题")
        if content is not None:
            memo["content"] = _clean_required(content, "备忘录内容")
        if evidence is not None:
            memo["evidence"] = evidence.strip()
        if tags is not None:
            memo["tags"] = _clean_tags(tags)
        memo["updated_at"] = time.time()
        self._write(records)
        return memo

    def clear(self) -> int:
        records = self._read()
        if self.path.exists():
            self.path.unlink()
        return len(records)

    @staticmethod
    def _find_unique(records: list[dict[str, Any]], memo_id: str) -> dict[str, Any]:
        matches = [item for item in records if str(item.get("id", "")).startswith(memo_id)]
        if not matches:
            raise MemoError(f"找不到备忘录：{memo_id}")
        if len(matches) > 1:
            raise MemoError(f"备忘录 ID 不唯一，请输入更完整的 ID：{memo_id}")
        return matches[0]

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MemoError(f"无法读取备忘录：{exc}") from exc
        records = payload.get("memos", []) if isinstance(payload, dict) else []
        return [item for item in records if isinstance(item, dict) and item.get("id")]

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f".tmp-{os.getpid()}")
        payload = {"version": 1, "memos": records}
        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self.path)
        finally:
            if temp_path.exists():
                temp_path.unlink()


def render_memo_context(
    project_dir: str | Path,
    *,
    max_chars: int = MAX_MEMO_CONTEXT_CHARS,
) -> str:
    records = MemoStore(project_dir).list()
    if not records:
        return ""
    lines = []
    for memo in records:
        lines.append(f"### {memo['title']} [{memo['id']}]")
        lines.append(memo["content"])
        if memo.get("evidence"):
            lines.append(f"依据：{memo['evidence']}")
        if memo.get("tags"):
            lines.append(f"标签：{', '.join(memo['tags'])}")
        if memo.get("experiment_name"):
            lines.append(f"来源实验：{memo['experiment_name']}")
        lines.append("")
    return "\n".join(lines).strip()[:max_chars]


def _clean_required(value: str, label: str) -> str:
    cleaned = " ".join(value.split()) if label == "备忘录标题" else value.strip()
    if not cleaned:
        raise MemoError(f"{label}不能为空。")
    return cleaned


def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for tag in tags:
        value = " ".join(str(tag).split())
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:12]
