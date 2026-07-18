"""Agent tool for exporting the fixed Markdown paper."""

from aero.agent.runtime import Runtime
from aero.paper_export import (
    PaperExportError,
)
from aero.paper_export import (
    export_paper as _export_paper,
)
from aero.toolbox.paths import find_project_dir
from aero.toolbox.registry import register_tool


@register_tool(
    name="export_paper",
    description=(
        "把当前项目固定的 paper/main.md 导出为 LaTeX、Word 或 PDF。"
        "用户要求转换论文格式、生成 tex/docx/pdf 文件时使用。"
        "使用 Pandoc 保留标题、列表、表格、图片引用、代码块、脚注和数学公式；"
        "不接受自定义输入或输出路径。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["latex", "word", "pdf"],
                "description": "目标格式：latex、word 或 pdf。",
            },
        },
        "required": ["format"],
    },
)
async def export_paper(format: str) -> dict:
    try:
        env = Runtime._build_exec_env()
        result = _export_paper(find_project_dir(), format, env=env)
        return {"success": True, **result}
    except PaperExportError as exc:
        message = str(exc)
        if exc.missing_tools:
            return {
                "success": False,
                "error": message,
                "tool_missing": True,
                "required_tools": exc.missing_tools,
                "suggested_action": "安装缺失的论文导出组件后重试。",
            }
        return {"success": False, "error": message}
