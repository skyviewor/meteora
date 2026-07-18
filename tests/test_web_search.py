import pytest

from aero.core.config import AeroConfig
from aero.data.web_search import _build_arguments, _normalize_search_response
from aero.toolbox.tools import web_search


def test_build_arguments_adapts_to_mcp_schema():
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "count": {"type": "integer"},
            "freshness": {"type": "integer"},
            "domains": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query"],
    }

    arguments = _build_arguments(
        schema,
        "最近一次西太平洋台风",
        limit=6,
        freshness_days=7,
        domains=["cma.gov.cn"],
    )

    assert arguments == {
        "query": "最近一次西太平洋台风",
        "count": 6,
        "freshness": 7,
        "domains": ["cma.gov.cn"],
    }


def test_build_arguments_falls_back_to_search_operators():
    schema = {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    }

    arguments = _build_arguments(
        schema,
        "台风名称",
        limit=8,
        freshness_days=30,
        domains=["cma.gov.cn", "jma.go.jp"],
    )

    assert arguments["q"] == (
        "台风名称 site:cma.gov.cn OR site:jma.go.jp 最近30天"
    )


def test_normalize_search_response_returns_structured_results_and_encoded_urls():
    raw = {
        "is_error": False,
        "text": "",
        "structured": {
            "results": [
                {
                    "title": "台风公报",
                    "url": "https://example.com/search?q=western pacific",
                    "summary": "最新台风信息",
                    "publish_time": "2026-07-18",
                }
            ]
        },
    }

    result = _normalize_search_response(raw, limit=8)

    assert result["found"] is True
    assert result["results"][0]["title"] == "台风公报"
    assert result["results"][0]["snippet"] == "最新台风信息"
    assert result["references"] == [
        "https://example.com/search?q=western%20pacific"
    ]


@pytest.mark.asyncio
async def test_search_web_reuses_vision_key_without_returning_it(monkeypatch):
    config = AeroConfig.create_default()
    config.vision.api_key = "sk-vision-secret"
    monkeypatch.setattr(web_search, "find_config", lambda: config)
    captured = {}

    async def fake_search(api_key, query, **kwargs):
        captured.update(api_key=api_key, query=query, kwargs=kwargs)
        return {
            "found": True,
            "results": [
                {
                    "title": "中央气象台台风公报",
                    "url": "https://www.nmc.cn/publish/typhoon/warning.html",
                    "snippet": "台风信息",
                }
            ],
            "content": "",
            "references": ["https://www.nmc.cn/publish/typhoon/warning.html"],
        }

    monkeypatch.setattr(web_search, "search_bailian_web", fake_search)

    result = await web_search.search_web(
        "最近一次西太平洋台风",
        freshness_days=30,
        domains=["nmc.cn"],
    )

    assert captured["api_key"] == "sk-vision-secret"
    assert captured["query"] == "最近一次西太平洋台风"
    assert result["provider"] == "阿里云百炼联网搜索"
    assert result["api_key_configured"] is True
    assert result["credential_reused"] is True
    assert "sk-vision-secret" not in repr(result)


@pytest.mark.asyncio
async def test_search_web_guides_setup_when_vision_key_is_missing(monkeypatch):
    config = AeroConfig.create_default()
    config.vision.api_key = ""
    monkeypatch.setattr(web_search, "find_config", lambda: config)

    result = await web_search.search_web("杭州天气")

    assert result["found"] is False
    assert result["api_key_configured"] is False
    assert result["credential_reused"] is False
    assert "百炼 API Key" in result["error"]
    assert result["references"]


@pytest.mark.asyncio
async def test_search_web_explains_unavailable_mcp_service(monkeypatch):
    config = AeroConfig.create_default()
    config.vision.api_key = "sk-test"
    monkeypatch.setattr(web_search, "find_config", lambda: config)

    async def fail(*args, **kwargs):
        raise ExceptionGroup("MCP request failed", [RuntimeError("Session terminated")])

    monkeypatch.setattr(web_search, "search_bailian_web", fail)

    result = await web_search.search_web("杭州天气")

    assert result["found"] is False
    assert result["api_key_configured"] is True
    assert result["credential_reused"] is True
    assert "无需重新提供或配置 Key" in result["error"]
    assert "启用 WebSearch" in result["action_required"]
    assert len(result["references"]) == 2


def test_search_web_is_registered_without_confirmation():
    from aero.toolbox.registry import get_registry

    spec = get_registry().get("search_web")

    assert spec is not None
    assert spec.requires_confirmation is False
    assert "最新信息" in spec.description
