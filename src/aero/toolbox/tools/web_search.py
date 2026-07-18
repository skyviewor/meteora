"""General web search tool."""

from __future__ import annotations

from aero.data.web_search import (
    WEB_SEARCH_CONSOLE_URL,
    WEB_SEARCH_GUIDE_URL,
    search_bailian_web,
)
from aero.toolbox.config_access import find_config
from aero.toolbox.registry import register_tool


@register_tool(
    name="search_web",
    description=(
        "搜索互联网中的最新信息和普通网页，返回标题、摘要、发布日期和来源链接。"
        "适用于实时天气、台风、新闻、近期事件、网站资料和模型知识截止日期之后的信息。"
        "学术论文优先使用专门的学术文献检索能力。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "完整、明确的自然语言搜索问题或关键词",
            },
            "limit": {
                "type": "integer",
                "description": "最多返回的搜索结果数，默认 8，范围 1 到 10",
                "minimum": 1,
                "maximum": 10,
            },
            "freshness_days": {
                "type": "integer",
                "description": "只关注最近多少天的内容；不限制时不要传",
                "minimum": 1,
                "maximum": 365,
            },
            "domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "优先限定的权威网站域名，最多 5 个，如 cma.gov.cn",
                "maxItems": 5,
            },
        },
        "required": ["query"],
    },
)
async def search_web(
    query: str,
    limit: int = 8,
    freshness_days: int | None = None,
    domains: list[str] | None = None,
) -> dict:
    """Search current web content using the configured Bailian credential."""
    config = find_config()
    api_key = config.vision.api_key.strip()
    if not api_key:
        return {
            "found": False,
            "api_key_configured": False,
            "credential_reused": False,
            "error": "尚未配置百炼 API Key，联网搜索暂不可用。",
            "message": "请先配置视觉模型使用的百炼 API Key；联网搜索会自动复用该凭证。",
            "references": [WEB_SEARCH_CONSOLE_URL],
        }

    try:
        result = await search_bailian_web(
            api_key,
            query,
            limit=limit,
            freshness_days=freshness_days,
            domains=domains,
        )
    except ValueError as exc:
        return {"found": False, "error": str(exc)}
    except Exception as exc:
        return _search_error(_exception_text(exc))

    result.update(
        {
            "query": query.strip(),
            "provider": "阿里云百炼联网搜索",
            "api_key_configured": True,
            "credential_reused": True,
            "credential_source": "视觉模型的百炼配置",
        }
    )
    if not result["found"]:
        result["message"] = "没有找到匹配的网页，请调整关键词或放宽时间和域名限制。"
    return result


def _search_error(error: str) -> dict:
    lowered = error.lower()
    if "session terminated" in lowered or "401" in lowered or "403" in lowered:
        message = (
            "已复用视觉模型配置的百炼 API Key，无需重新提供或配置 Key。"
            "百炼拒绝建立联网搜索会话，通常是因为当前账号尚未在 MCP 市场启用 "
            "WebSearch、服务协议尚未确认，或搜索额度已经用尽。"
        )
        action_required = "在百炼 MCP 市场启用 WebSearch 并确认服务状态"
    elif "timeout" in lowered or "timed out" in lowered:
        message = "联网搜索请求超时，请稍后重试。"
        action_required = "稍后重试"
    else:
        message = "联网搜索暂时失败，请稍后重试或检查百炼联网搜索服务状态。"
        action_required = "稍后重试或检查百炼联网搜索服务状态"
    return {
        "found": False,
        "api_key_configured": True,
        "credential_reused": True,
        "credential_source": "视觉模型的百炼配置",
        "action_required": action_required,
        "error": message,
        "references": [WEB_SEARCH_CONSOLE_URL, WEB_SEARCH_GUIDE_URL],
    }


def _exception_text(exception: BaseException) -> str:
    messages: list[str] = []

    def walk(current: BaseException) -> None:
        message = str(current).strip()
        if message and message not in messages:
            messages.append(message)
        children = getattr(current, "exceptions", ())
        for child in children:
            if isinstance(child, BaseException):
                walk(child)
        if current.__cause__ is not None:
            walk(current.__cause__)

    walk(exception)
    return " | ".join(messages)
