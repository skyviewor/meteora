"""Tests for local LLM setup helpers."""

import pytest

from aero.cli.main import (
    AeroApp,
    _extract_llm_api_key,
    _is_bare_api_key,
    _mask_secret_text,
    _parse_llm_clear_from_text,
    _parse_llm_setup_from_text,
    _requests_vision_key_reuse,
)
from aero.core.config import AeroConfig


def test_parse_qwen_setup_uses_bailian():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text(
        "配置一下 qwen3.7 模型，API key: sk-test-0004",
        config,
    )

    assert setup is not None
    assert setup["provider"] == "bailian"
    assert setup["model"] == "qwen3.7"
    assert setup["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert setup["api_key"] == "sk-test-0004"


def test_parse_kimi_provider_does_not_use_provider_name_as_model():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text(
        "帮我配置一下 kimi 模型，api key 是: sk-test-0005",
        config,
    )

    assert setup is not None
    assert setup["provider"] == "kimi"
    assert setup["model"] == "kimi-k2.6"
    assert setup["base_url"] == "https://api.moonshot.cn/v1"
    assert setup["api_key"] == "sk-test-0005"


def test_parse_explicit_kimi_model():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text(
        "配置 kimi-k2-thinking，API key: sk-test-0006",
        config,
    )

    assert setup is not None
    assert setup["provider"] == "kimi"
    assert setup["model"] == "kimi-k2-thinking"


def test_parse_key_only_keeps_current_provider_model():
    config = AeroConfig.create_default()
    config.llm.provider = "deepseek"
    config.llm.model = "deepseek-chat"

    setup = _parse_llm_setup_from_text("换 key: sk-test-0002", config)

    assert setup is not None
    assert setup["provider"] == "deepseek"
    assert setup["model"] == "deepseek-chat"
    assert setup["api_key"] == "sk-test-0002"


def test_parse_clear_key_intent_takes_priority_over_setup():
    config = AeroConfig.create_default()

    clear = _parse_llm_clear_from_text("帮我清理掉模型的 API key")
    setup = _parse_llm_setup_from_text("帮我清理掉模型的 API key", config)

    assert clear == {"reset_provider": False}
    assert setup is None


def test_parse_vision_model_setup_does_not_route_to_main_llm():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text("视觉模型配置了吗？", config)
    clear = _parse_llm_clear_from_text("清除视觉模型 API key")

    assert setup is None
    assert clear is None


def test_parse_merra2_credentials_does_not_route_to_main_llm():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text("怎么配置 MERRA-2 凭证", config)
    clear = _parse_llm_clear_from_text("清除 MERRA-2 Earthdata token")

    assert setup is None
    assert clear is None


def test_parse_cams_ads_credentials_does_not_route_to_main_llm():
    config = AeroConfig.create_default()

    setup = _parse_llm_setup_from_text("帮我配置 CAMS ADS API key", config)
    clear = _parse_llm_clear_from_text("清除 CAMS ADS key")

    assert setup is None
    assert clear is None


def test_parse_full_reset_llm_intent():
    clear = _parse_llm_clear_from_text("完整重置模型 API key 和服务商")

    assert clear == {"reset_provider": True}


def test_mask_secret_text():
    text = "配置 qwen3.7，API key: sk-test-0004"

    assert _extract_llm_api_key(text) == "sk-test-0004"
    assert _mask_secret_text(text) == "配置 qwen3.7，API key: sk-t...0004"


def test_bare_api_key_detection():
    assert _is_bare_api_key("sk-test-0004") is True
    assert _is_bare_api_key("API key: sk-test-0004") is False
    assert _is_bare_api_key("请使用 sk-test-0004 配置视觉模型") is False


def test_detect_vision_key_reuse_request():
    assert _requests_vision_key_reuse("你直接复用视觉模型的 API Key") is True
    assert _requests_vision_key_reuse("切换主模型 API Key") is False


@pytest.mark.asyncio
async def test_bare_api_key_is_masked_and_never_starts_agent():
    config = AeroConfig.create_default()
    config.vision.api_key = "sk-existing-vision"
    app = AeroApp(config, persist_config=False)

    async with app.run_test(size=(100, 30)):
        await app._process("sk-new-sensitive-value")

    transcript = "\n".join(app._chat_log)
    assert "sk-new-sensitive-value" not in transcript
    assert "sk-n...alue" in transcript
    assert app._agent_worker is None
