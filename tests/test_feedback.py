"""Tests for user-feedback issue drafts."""

from urllib.parse import parse_qs, unquote, urlparse

import pytest

from aero.agent.system_prompt import build_system_prompt
from aero.core.config import AeroConfig
from aero.toolbox.registry import get_registry
from aero.toolbox.tools.feedback import prepare_issue_link


@pytest.mark.asyncio
async def test_prepare_issue_link_builds_prefilled_github_draft():
    result = await prepare_issue_link(
        title="改善模型配置失败提示",
        problem="连通性测试把上游 503 描述成配置错误。",
        expected="区分服务暂不可用和用户配置错误。",
        actual="界面统一提示检查 API Key、接口地址和模型 ID。",
        reproduction_steps=["打开主模型配置页。", "输入配置并运行连通性测试。"],
        context="主模型配置页。",
    )

    # Textual decodes Markdown hrefs once before opening them.
    parsed = urlparse(unquote(result["issue_url"]))
    query = parse_qs(parsed.query)

    assert parsed.netloc == "github.com"
    assert parsed.path == "/skyviewor/Aerolytica/issues/new"
    assert query["title"] == ["改善模型配置失败提示"]
    assert "## 问题或需求" in query["body"][0]
    assert "## 期望结果" in query["body"][0]
    assert "## 当前表现" in query["body"][0]
    assert "## 复现步骤" in query["body"][0]
    assert "1. 打开主模型配置页。" in query["body"][0]
    assert result["message"].endswith("手动提交。")


@pytest.mark.asyncio
async def test_issue_link_protects_markdown_and_unicode_from_textual_decoding():
    result = await prepare_issue_link(
        title="改善 GIS 导出",
        problem="中文 Issue 链接打开后出现乱码。",
        expected="标题和正文保持 UTF-8 中文。",
    )

    clicked_url = unquote(result["issue_url"])
    parsed = urlparse(clicked_url)
    query = parse_qs(parsed.query)

    assert parsed.fragment == ""
    assert query["title"] == ["改善 GIS 导出"]
    assert "## 问题或需求" in query["body"][0]
    assert "中文 Issue 链接打开后出现乱码。" in query["body"][0]


@pytest.mark.asyncio
async def test_prepare_issue_link_rejects_incomplete_draft():
    with pytest.raises(ValueError, match="不能为空"):
        await prepare_issue_link(title="", problem="问题", expected="期望")


@pytest.mark.asyncio
async def test_prepare_issue_link_redacts_sensitive_conversation_context():
    result = await prepare_issue_link(
        title="配置失败",
        problem="使用 sk-super-secret-12345678 后失败，联系 me@example.com。",
        expected="正常连接。",
        actual="Authorization: Bearer abcdefghijklmnop",
        reproduction_steps=[
            "读取 /Users/alice/project/aero.yaml",
            "设置 api_key=nvapi-abcdefghijklmnop",
        ],
        context="token: private-token-value；目录 /home/bob/work",
    )

    body = result["body"]

    assert "sk-super-secret" not in body
    assert "me@example.com" not in body
    assert "abcdefghijklmnop" not in body
    assert "/Users/alice" not in body
    assert "/home/bob" not in body
    assert "[REDACTED API KEY]" in body
    assert "[REDACTED EMAIL]" in body
    assert "/Users/[USER]/project/aero.yaml" in body
    assert "/home/[USER]/work" in body


def test_feedback_tool_is_registered_without_submission_confirmation():
    spec = get_registry().get("prepare_issue_link")

    assert spec is not None
    assert spec.requires_confirmation is False
    assert "明确同意" in spec.description
    assert "不会提交 Issue" in spec.description


@pytest.mark.parametrize("language", ["zh", "en"])
def test_system_prompt_requires_consent_before_issue_link(language):
    prompt = build_system_prompt(AeroConfig.create_default(), language)

    assert "prepare_issue_link" in prompt
    if language == "zh":
        assert "用户明确同意前不得生成链接" in prompt
        assert "最小复现步骤" in prompt
        assert "用户直接要求创建或提交 Issue 时已经构成同意" in prompt
        assert "绝不能声称 Issue 已经提交" in prompt
    else:
        assert "Do not generate a link until the user explicitly agrees" in prompt
        assert "minimal ordered reproduction steps" in prompt
        assert "direct request to create or submit an Issue already counts as consent" in prompt
        assert "Never claim the Issue was submitted" in prompt
