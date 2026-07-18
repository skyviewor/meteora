"""Agent tools for single-document Markdown paper version history."""

from datetime import datetime

from aero.paper_versions import PaperVersionManager
from aero.toolbox.paths import find_project_dir
from aero.toolbox.registry import register_tool


def _manager() -> PaperVersionManager:
    return PaperVersionManager(find_project_dir())


@register_tool(
    name="initialize_paper_versioning",
    description=(
        "为当前项目固定的 paper/main.md 论文正文启用独立版本控制并保存初始版本。"
        "目录或文件不存在时会自动创建。"
        "仅当用户明确要求开始追踪、管理论文版本或初始化论文版本库时使用。"
        "不接受自定义路径，不会追踪图片、数据、脚本或其他文件。"
    ),
    parameters={"type": "object", "properties": {}},
)
async def initialize_paper_versioning() -> dict:
    try:
        return {"success": True, **_manager().initialize()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="paper_version_status",
    description=(
        "查看论文版本控制状态，包括绑定的 Markdown 正文、当前版本、版本数量"
        "以及正文相对当前版本是否有未保存变化。"
    ),
    parameters={"type": "object", "properties": {}},
)
async def paper_version_status() -> dict:
    try:
        return {"success": True, **_manager().status()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="save_paper_version",
    description=(
        "仅当用户明确要求保存、提交或建立论文版本时，保存当前 Markdown 正文的新版本。"
        "只保存已绑定的论文正文；内容未变化时不会重复创建版本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "简短说明本版论文的主要变化。",
            },
        },
    },
)
async def save_paper_version(title: str = "") -> dict:
    try:
        return {"success": True, "version": _manager().save(title)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="list_paper_versions",
    description=(
        "查看论文正文的版本历史。默认隐藏恢复前自动保存的保护版本；"
        "只有用户明确要求查看全部版本时才包含保护版本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "include_safety": {
                "type": "boolean",
                "description": "是否包含恢复前保护版本，默认 false。",
            },
        },
    },
)
async def list_paper_versions(include_safety: bool = False) -> dict:
    try:
        versions = _manager().list(include_safety=include_safety)
        return {"success": True, "count": len(versions), "versions": versions}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="diff_paper_version",
    description=(
        "逐行比较当前论文正文与一个已保存版本。未指定版本时与当前版本比较，"
        "返回新增行数、删除行数和统一 diff 文本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "version_id": {
                "type": "string",
                "description": "可选的论文版本 ID 或完整标题。",
            },
        },
    },
)
async def diff_paper_version(version_id: str = "") -> dict:
    try:
        return {"success": True, **_manager().diff(version_id or None).to_dict()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="restore_paper_version",
    description=(
        "把已绑定的 Markdown 论文正文恢复到指定版本，执行前必须让用户确认。"
        "只覆盖这一份正文，不修改其他文件；若当前正文有未保存变化，"
        "恢复前会自动保存一个保护版本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "version_id": {
                "type": "string",
                "description": "要恢复的论文版本 ID 或完整标题。",
            },
        },
        "required": ["version_id"],
    },
    requires_confirmation=True,
)
async def restore_paper_version(version_id: str) -> dict:
    try:
        result = _manager().restore(version_id)
        restored = result["restored"]
        return {
            "success": True,
            "document": result["document"],
            "restored_version": {
                "id": restored["id"],
                "title": restored["title"],
                "created_at": datetime.fromtimestamp(restored["created_at"]).isoformat(
                    timespec="seconds"
                ),
            },
            "protection_version": result["protection_version"],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
