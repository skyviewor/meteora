"""Checkpoint discovery and creation tools for the agent."""

from __future__ import annotations

from datetime import datetime

from aero.agent.checkpoint_context import create_checkpoint_from_context
from aero.checkpoints import CheckpointError, CheckpointManager
from aero.experiments import ExperimentError, ExperimentManager
from aero.toolbox.paths import find_project_dir
from aero.toolbox.registry import register_tool


def _active_checkpoint_manager() -> CheckpointManager:
    project_dir = find_project_dir()
    experiment_manager = ExperimentManager(project_dir)
    experiment = experiment_manager.active()
    if experiment is None:
        return CheckpointManager(project_dir)
    return CheckpointManager(
        experiment_manager.workspace_path(experiment),
        experiment_id=experiment["id"],
    )


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
        "只查询当前作用域：实验中仅返回该实验的检查点，主流程中仅返回主流程检查点。"
        "默认不返回系统自动创建的恢复保护记录；仅当用户明确要求查看全部或恢复保护记录时才包含。"
        "回复列表时默认只显示检查点名称、保存时间和 ID；用户明确询问时再补充其他信息。"
        "不要暴露工具名。"
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
    all_checkpoints = _active_checkpoint_manager().list()
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
        checkpoint = _active_checkpoint_manager().rename(checkpoint_id, name)
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
        diff = _active_checkpoint_manager().diff(checkpoint_id)
        return {"success": True, **diff.to_dict()}
    except CheckpointError as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="start_checkpoint_experiment",
    description=(
        "仅当用户明确要求从当前状态开始新的实验分支时使用。"
        "会创建独立实验工作区及 scripts、figures、plans、outputs、reports、data 等目录，"
        "后续相对路径默认写入该实验。回复时称为‘实验’，不要暴露工具名或 Git 概念。"
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
        project_dir = find_project_dir()
        checkpoint_manager = _active_checkpoint_manager()
        state = ExperimentManager(project_dir).create(
            name,
            base_checkpoint=checkpoint_manager.current_checkpoint_id(),
        )
        return {
            "success": True,
            "experiment_id": state["id"],
            "name": state["name"],
            "workspace": state["workspace"],
            "base_checkpoint": state.get("base_checkpoint"),
        }
    except (CheckpointError, ExperimentError) as exc:
        return {"success": False, "error": str(exc)}
