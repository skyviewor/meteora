"""Checkpoint discovery and creation tools for the agent."""

from __future__ import annotations

from datetime import datetime

from aero.agent.checkpoint_context import create_checkpoint_from_context
from aero.checkpoints import CheckpointError, CheckpointManager, checkpoint_progress_label
from aero.toolbox.paths import find_project_dir
from aero.toolbox.registry import register_tool


@register_tool(
    name="create_checkpoint",
    description=(
        "仅当用户明确要求保存当前进度、创建检查点或建立恢复点时使用。"
        "保存当前加密对话、可恢复的小文件和仅记录状态的大型数据。"
        "回复用户时只说‘检查点’，不要暴露工具名。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "用户可理解的检查点名称"},
        },
    },
)
async def create_checkpoint(name: str = "") -> dict:
    try:
        checkpoint = create_checkpoint_from_context(name)
        if checkpoint.get("success") is False:
            return checkpoint
        exact = sum(1 for item in checkpoint.get("files", []) if item.get("restore") == "exact")
        references = len(checkpoint.get("files", [])) - exact
        return {
            "success": True,
            "checkpoint_id": checkpoint["id"],
            "name": checkpoint["name"],
            "created_at": checkpoint["created_at"],
            "exact_files": exact,
            "data_references": references,
            "exact_restore": checkpoint["exact_restore"],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="list_checkpoints",
    description=(
        "用户询问已保存的检查点、恢复点或实验历史时使用。"
        "默认不返回系统自动创建的恢复保护记录；仅当用户明确要求查看全部或恢复保护记录时才包含。"
        "回复中使用自然语言和检查点 ID，不要暴露工具名。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "include_safety": {
                "type": "boolean",
                "description": "是否包含恢复前自动创建的保护记录，默认 false",
            },
        },
    },
)
async def list_checkpoints(include_safety: bool = False) -> dict:
    all_checkpoints = CheckpointManager(find_project_dir()).list()
    safety_count = sum(1 for item in all_checkpoints if item.get("kind") == "pre-restore")
    checkpoints = (
        all_checkpoints
        if include_safety
        else [item for item in all_checkpoints if item.get("kind") != "pre-restore"]
    )
    return {
        "success": True,
        "hidden_safety_count": 0 if include_safety else safety_count,
        "checkpoints": [
            {
                "id": item["id"],
                "name": item["name"],
                "created_at": datetime.fromtimestamp(item["created_at"]).isoformat(),
                "progress": checkpoint_progress_label(item) or "默认进度",
                "exact_restore": item.get("exact_restore", False),
                "recovery_protection": item.get("kind") == "pre-restore",
            }
            for item in checkpoints
        ],
    }


@register_tool(
    name="rename_checkpoint",
    description=(
        "仅当用户明确要求修改某个检查点的名称时使用。"
        "此操作不会改变检查点内容、ID、恢复关系或创建时间。"
        "回复中使用自然语言和检查点 ID，不要暴露工具名。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "checkpoint_id": {"type": "string", "description": "检查点 ID 或完整名称"},
            "name": {"type": "string", "description": "新的检查点名称"},
        },
        "required": ["checkpoint_id", "name"],
    },
)
async def rename_checkpoint(checkpoint_id: str, name: str) -> dict:
    try:
        checkpoint = CheckpointManager(find_project_dir()).rename(checkpoint_id, name)
        return {
            "success": True,
            "checkpoint_id": checkpoint["id"],
            "name": checkpoint["name"],
        }
    except CheckpointError as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="compare_checkpoint",
    description=(
        "用户要求查看当前工作区与某个检查点的差异时使用。"
        "此操作只读取状态，不恢复或覆盖文件。回复时不要暴露工具名。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "checkpoint_id": {"type": "string", "description": "检查点 ID 或完整名称"},
        },
        "required": ["checkpoint_id"],
    },
)
async def compare_checkpoint(checkpoint_id: str) -> dict:
    try:
        diff = CheckpointManager(find_project_dir()).diff(checkpoint_id)
        return {"success": True, **diff.to_dict()}
    except CheckpointError as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="start_checkpoint_experiment",
    description=(
        "仅当用户明确要求从当前状态开始新的实验分支时使用。"
        "不会修改文件。回复时称为‘实验分支’，不要暴露工具名或 Git 概念。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "实验分支名称"},
        },
        "required": ["name"],
    },
)
async def start_checkpoint_experiment(name: str) -> dict:
    try:
        state = CheckpointManager(find_project_dir()).start_experiment(name)
        return {
            "success": True,
            "name": state["experiment"],
            "base_checkpoint": state.get("experiment_base"),
        }
    except CheckpointError as exc:
        return {"success": False, "error": str(exc)}
