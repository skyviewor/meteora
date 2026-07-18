"""Research memo tools."""

from aero.toolbox.paths import find_project_dir, short_path
from aero.toolbox.registry import register_tool


@register_tool(
    name="record_memo",
    description=(
        "提议把一条可复用的研究结论加入当前项目备忘录。"
        "用户明确说把某个结论记下来时必须调用；调用后界面会展示完整内容并要求用户确认，"
        "确认前不会保存。title 应简短，content 应是自洽的结论，evidence 记录数据、图表、"
        "统计结果或限制条件，不能把猜测写成已验证事实。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "简短、可检索的备忘录标题。",
            },
            "content": {
                "type": "string",
                "description": "脱离当前对话也能理解的研究结论。",
            },
            "evidence": {
                "type": "string",
                "description": "支持该结论的文件、图表、统计值、文献或适用限制。",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "用于检索的主题标签，例如 ozone、CAMS、敏感性分析。",
            },
        },
        "required": ["title", "content"],
    },
    requires_confirmation=True,
)
async def record_memo(
    title: str,
    content: str,
    evidence: str = "",
    tags: list[str] | None = None,
) -> dict:
    from aero.data.memos import MemoStore
    from aero.experiments import ExperimentManager

    project_dir = find_project_dir()
    experiment = ExperimentManager(project_dir).active()
    memo, created = MemoStore(project_dir).add(
        title=title,
        content=content,
        evidence=evidence,
        tags=tags,
        experiment_id=experiment["id"] if experiment else None,
        experiment_name=experiment["name"] if experiment else None,
    )
    return {
        "success": True,
        "created": created,
        "memo": memo,
        "saved_to": short_path(MemoStore(project_dir).path),
        "message": "已加入备忘录。" if created else "相同内容已在备忘录中。",
    }


@register_tool(
    name="show_memos",
    description=(
        "查看当前项目的研究备忘录，可按标题、正文、依据或标签检索。"
        "用户要求总结研究发现、整理结论或写论文前，应优先查看相关备忘录。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "可选的检索关键词。"},
            "limit": {
                "type": "integer",
                "description": "最多返回多少条，默认 50。",
                "minimum": 1,
                "maximum": 100,
            },
        },
    },
)
async def show_memos(query: str = "", limit: int = 50) -> dict:
    from aero.data.memos import MemoStore

    memos = MemoStore(find_project_dir()).list(query=query, limit=max(1, min(limit, 100)))
    return {
        "success": True,
        "count": len(memos),
        "query": query,
        "memos": memos,
        "message": "暂无匹配的备忘录。" if not memos else f"找到 {len(memos)} 条备忘录。",
    }


@register_tool(
    name="update_memo",
    description=(
        "补充或修正一条已有研究备忘录，执行前必须让用户确认。"
        "当用户要给已有结论补充名称、证据、限制或更正内容时使用；"
        "不得为了更新备忘录而先删除旧记录。未提供的字段保持不变。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "memo_id": {"type": "string", "description": "要更新的备忘录 ID。"},
            "title": {"type": "string", "description": "可选的新标题。"},
            "content": {"type": "string", "description": "可选的完整新正文。"},
            "evidence": {"type": "string", "description": "可选的新依据或限制。"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "可选的新标签列表。",
            },
        },
        "required": ["memo_id"],
    },
    requires_confirmation=True,
)
async def update_memo(
    memo_id: str,
    title: str | None = None,
    content: str | None = None,
    evidence: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    from aero.data.memos import MemoStore

    try:
        memo = MemoStore(find_project_dir()).update(
            memo_id,
            title=title,
            content=content,
            evidence=evidence,
            tags=tags,
        )
        return {"success": True, "memo": memo, "message": "备忘录已更新。"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="delete_memo",
    description=(
        "仅当用户本轮明确要求删除时，按 ID 永久删除一条研究备忘录并要求确认。"
        "补充、更正、替换或记录结论时严禁使用，应改为更新或新增备忘录。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "memo_id": {"type": "string", "description": "要删除的备忘录 ID。"},
        },
        "required": ["memo_id"],
    },
    requires_confirmation=True,
)
async def delete_memo(memo_id: str) -> dict:
    from aero.data.memos import MemoStore

    try:
        memo = MemoStore(find_project_dir()).delete(memo_id)
        return {"success": True, "deleted": memo, "message": "备忘录已删除。"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool(
    name="clear_memos",
    description=(
        "仅当用户本轮明确要求清空全部备忘录时，永久清理当前项目的全部研究备忘录，"
        "执行前必须让用户确认。不得用于更新、整理或替换备忘录。"
    ),
    parameters={"type": "object", "properties": {}},
    requires_confirmation=True,
)
async def clear_memos() -> dict:
    from aero.data.memos import MemoStore

    try:
        count = MemoStore(find_project_dir()).clear()
        return {"success": True, "deleted_count": count, "message": f"已清理 {count} 条备忘录。"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
