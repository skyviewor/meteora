"""Tests for the first-run model setup wizard."""

import pytest
from rich.table import Table
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, OptionList, Static

from aero.cli.main import (
    AeroApp,
    SelectScreen,
    _model_options,
)
from aero.cli.setup_wizard import FirstRunSetupScreen
from aero.core.config import AeroConfig, LLMProviderConfig
from aero.core.llm_providers import BUILTIN_LLM_PROVIDERS, model_tags


class WizardHost(App[None]):
    def __init__(self, **wizard_kwargs) -> None:
        super().__init__()
        self.wizard_kwargs = wizard_kwargs
        self.result: dict | None = None

    def compose(self) -> ComposeResult:
        yield OptionList()

    def on_mount(self) -> None:
        self.push_screen(
            FirstRunSetupScreen(**self.wizard_kwargs),
            self._capture_result,
        )

    def _capture_result(self, result: dict | None) -> None:
        self.result = result


@pytest.mark.asyncio
async def test_wizard_starts_with_official_and_custom_model_sources():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        options = wizard.query_one("#setup-list", OptionList)
        assert options.option_count == 2
        assert options.get_option_at_index(0).id == "custom"
        assert options.get_option_at_index(1).id == "official"


@pytest.mark.asyncio
async def test_wizard_offers_primary_reuse_for_known_multimodal_model():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._primary = {
            "provider": "openai",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
        }
        wizard._primary_supports_vision = True
        wizard._page = "vision_mode"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        assert options.get_option_at_index(0).id == "reuse_primary"


@pytest.mark.asyncio
async def test_web_search_hides_duplicate_bailian_setup_when_key_can_be_reused():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._vision = {
            "mode": "separate",
            "provider": "bailian",
            "api_key": "sk-bailian",
        }
        wizard._page = "web_search_setup"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        option_ids = [options.get_option_at_index(i).id for i in range(options.option_count)]
        assert option_ids == ["skip", "reuse_bailian", "configure_zhipu"]


@pytest.mark.asyncio
async def test_web_search_keeps_bailian_setup_without_reusable_key():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._vision = {"mode": "separate", "provider": "bailian", "api_key": ""}
        wizard._page = "web_search_setup"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        option_ids = [options.get_option_at_index(i).id for i in range(options.option_count)]
        assert option_ids == ["skip", "configure_bailian", "configure_zhipu"]


@pytest.mark.asyncio
async def test_web_search_hides_duplicate_zhipu_setup_when_key_can_be_reused():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._vision = {
            "mode": "separate",
            "provider": "zhipu",
            "api_key": "sk-zhipu",
        }
        wizard._page = "web_search_setup"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        option_ids = [options.get_option_at_index(i).id for i in range(options.option_count)]
        assert option_ids == ["skip", "configure_bailian", "reuse_zhipu"]


@pytest.mark.asyncio
async def test_web_search_defaults_to_reusing_primary_bailian_key():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._primary = {"provider": "bailian", "api_key": "sk-bailian-primary"}
        wizard._page = "web_search_setup"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        option_ids = [options.get_option_at_index(i).id for i in range(options.option_count)]
        assert option_ids == ["reuse_bailian", "skip", "configure_zhipu"]
        assert options.highlighted == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["bailian", "zhipu"])
async def test_web_search_form_only_shows_api_key(provider):
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._web_search = {"configured": True, "provider": provider}
        wizard._page = "web_search_form"
        wizard._render_page()
        assert wizard.query_one("#setup-url", Input).display is False
        assert wizard.query_one("#setup-model", Input).display is False
        assert wizard.query_one("#setup-key", Input).display is True
        assert wizard.focused is not None
        assert wizard.focused.id == "setup-key"


@pytest.mark.asyncio
async def test_preset_provider_only_shows_api_key_and_key_acquisition_help():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._primary = {"provider": "deepseek"}
        wizard._page = "primary_form"
        wizard._render_page()
        assert wizard.query_one("#setup-url").value == "https://api.deepseek.com"
        assert wizard.query_one("#setup-model").value == "deepseek-v4-flash"
        assert wizard.query_one("#setup-url", Input).display is False
        assert wizard.query_one("#setup-model", Input).display is False
        assert wizard.query_one("#setup-key").placeholder == "API Key"
        help_text = wizard.query_one("#setup-provider-help", Static)
        assert help_text.display is True
        assert "platform.deepseek.com/api_keys" in str(help_text.render())
        assert wizard.focused is not None
        assert wizard.focused.id == "setup-key"


def test_preset_provider_key_urls_open_the_key_management_pages():
    assert BUILTIN_LLM_PROVIDERS["deepseek"].api_key_url == "https://platform.deepseek.com/api_keys"
    assert BUILTIN_LLM_PROVIDERS["bailian"].api_key_url.endswith("#/efm/api_key")
    assert BUILTIN_LLM_PROVIDERS["kimi"].api_key_url == "https://platform.kimi.com/console/api-keys"


@pytest.mark.asyncio
async def test_custom_provider_keeps_endpoint_and_model_fields_editable():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._primary = {"provider": "custom"}
        wizard._page = "primary_form"
        wizard._render_page()
        assert wizard.query_one("#setup-url", Input).display is True
        assert wizard.query_one("#setup-model", Input).display is True
        assert wizard.query_one("#setup-provider-help", Static).display is False


@pytest.mark.asyncio
async def test_deepseek_provider_opens_full_model_selection():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._page = "primary_provider"
        wizard._render_page()
        wizard._choose("deepseek")
        assert wizard._page == "primary_model"
        options = wizard.query_one("#setup-list", OptionList)
        model_ids = [
            options.get_option_at_index(index).id
            for index in range(options.option_count)
        ]
        assert model_ids == [
            "deepseek-v4-flash",
            "deepseek-v4-pro",
        ]


@pytest.mark.asyncio
async def test_bailian_provider_lists_all_preset_models():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._page = "primary_provider"
        wizard._render_page()
        wizard._choose("bailian")
        options = wizard.query_one("#setup-list", OptionList)
        model_ids = [
            options.get_option_at_index(index).id
            for index in range(options.option_count)
        ]
        assert model_ids == [
            "qwen3.7-max",
            "qwen3.7-plus",
            "qwen3.6-plus",
            "qwen3.6-flash",
            "qwen3.5-plus",
            "qwen3.5-flash",
        ]
        prompt = options.get_option_at_index(1).prompt
        assert isinstance(prompt, Table)
        assert [column.width for column in prompt.columns] == [22, 8, None, 4]
        assert [column.justify for column in prompt.columns[:3]] == [
            "left",
            "left",
            "left",
        ]
        assert prompt.columns[3].justify == "right"


@pytest.mark.asyncio
async def test_switching_to_provider_without_key_opens_setup_screen(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    config = AeroConfig.create_default()
    config.llm.provider = "bailian"
    config.llm.model = "qwen3.7-plus"
    config.llm.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    config.llm.providers["bailian"] = LLMProviderConfig(
        api_key="sk-bailian",
        model=config.llm.model,
        base_url=config.llm.base_url,
    )
    app = AeroApp(config, persist_config=False)

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        app._set_provider("deepseek")
        await pilot.pause()

        wizard = app.screen
        assert isinstance(wizard, FirstRunSetupScreen)
        assert wizard._primary_only is True
        assert wizard._primary["provider"] == "deepseek"
        assert wizard._primary["model"] == "deepseek-v4-flash"

        wizard.query_one("#setup-key", Input).value = "sk-deepseek"
        wizard._submit_form()
        await pilot.pause()

        assert app.config.llm.provider == "deepseek"
        assert app.config.llm.model == "deepseek-v4-flash"
        assert app.config.llm.active_api_key() == "sk-deepseek"


@pytest.mark.asyncio
async def test_primary_only_setup_reuses_provider_connection_form():
    app = WizardHost(
        primary_only=True,
        primary={
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "base_url": "https://api.deepseek.com",
        },
    )

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        assert wizard._page == "primary_form"
        assert wizard.query_one("#setup-url", Input).value == "https://api.deepseek.com"
        assert wizard.query_one("#setup-model", Input).value == "deepseek-v4-flash"
        assert wizard.query_one("#setup-back", Static).display is False
        assert wizard.query_one("#setup-skip", Static).display is False

        wizard.query_one("#setup-key", Input).value = "sk-test-provider"
        wizard._submit_form()
        await pilot.pause()

        assert app.result is not None
        assert app.result["primary"] == {
            "provider": "deepseek",
            "label": "deepseek",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
            "api_key": "sk-test-provider",
        }
        assert app.result["vision"]["mode"] == "unconfigured"


@pytest.mark.asyncio
async def test_setup_card_is_centered_with_visible_side_margins():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        dialog = app.screen.query_one("#setup-dialog")
        assert dialog.region.width == 76
        assert dialog.region.x == 12
        assert dialog.region.right == 88


@pytest.mark.asyncio
async def test_choice_page_can_move_to_back_and_cancel_with_keyboard():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._page = "primary_provider"
        wizard._render_page()
        options = wizard.query_one("#setup-list", OptionList)
        options.highlighted = options.option_count - 1
        options.focus()

        await pilot.press("down")
        assert wizard._action_focused is True
        assert wizard._selected_action == 2
        assert wizard.query_one("#setup-back").has_class("setup-selected")

        await pilot.press("right")
        assert wizard._selected_action == 3
        assert wizard.query_one("#setup-cancel").has_class("setup-selected")

        await pilot.press("up")
        assert wizard._action_focused is False
        assert wizard.focused is options


@pytest.mark.asyncio
async def test_form_can_reach_all_visible_actions_with_keyboard():
    app = WizardHost()

    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        wizard = app.screen
        wizard._primary = {"provider": "deepseek", "model": "deepseek-v4-flash"}
        wizard._page = "primary_form"
        wizard._render_page()
        wizard.set_focus(wizard.query_one("#setup-key"))

        await pilot.press("down")
        assert wizard._action_focused is True
        assert wizard._selected_action == 0

        await pilot.press("right")
        assert wizard._selected_action == 1
        assert wizard.query_one("#setup-skip").has_class("setup-selected")
        await pilot.press("right")
        assert wizard._selected_action == 2
        assert wizard.query_one("#setup-back").has_class("setup-selected")
        await pilot.press("right")
        assert wizard._selected_action == 3
        assert wizard.query_one("#setup-cancel").has_class("setup-selected")
        await pilot.press("left")
        assert wizard._selected_action == 2


def test_model_command_options_use_setup_feature_labels():
    for provider, preset in BUILTIN_LLM_PROVIDERS.items():
        options = _model_options(provider)
        assert [model for model, _ in options] == list(preset.models)

        for model, prompt in options:
            assert isinstance(prompt, Table)
            model_type, positioning = model_tags(provider, model)
            cells = [column._cells[0] for column in prompt.columns]
            assert cells[0] == model
            assert cells[1] == model_type
            assert cells[2] == positioning
            assert cells[3] == ("推荐" if model == preset.default_model else "")
            assert preset.name not in [str(cell) for cell in cells[1:]]


@pytest.mark.asyncio
async def test_model_command_picker_keeps_raw_model_ids_and_keyboard_selection(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    config = AeroConfig.create_default()
    config.llm.provider = "bailian"
    config.llm.model = "qwen3.7-plus"
    app = AeroApp(config, persist_config=False)

    async with app.run_test(size=(100, 30)) as pilot:
        app._handle_model_command("/model")
        await pilot.pause()

        assert isinstance(app.screen, SelectScreen)
        options = app.screen.query_one("#select-list", OptionList)
        assert options.highlighted == 1
        assert options.get_option_at_index(1).id == "qwen3.7-plus"
        outer_prompt = options.get_option_at_index(1).prompt
        assert isinstance(outer_prompt, Table)
        feature_prompt = outer_prompt.columns[1]._cells[0]
        assert isinstance(feature_prompt, Table)
        assert tuple(column._cells[0] for column in feature_prompt.columns[:3]) == (
            "qwen3.7-plus",
            "多模态",
            "均衡",
        )

        options.highlighted = 2
        await pilot.press("enter")
        await pilot.pause()

        assert config.llm.model == "qwen3.6-plus"


@pytest.mark.asyncio
async def test_model_picker_navigation_does_not_scroll_background_chat(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AERO_SECRETS_PATH", str(tmp_path / "secrets.yaml"))
    config = AeroConfig.create_default()
    config.llm.provider = "bailian"
    config.llm.model = "qwen3.7-plus"
    app = AeroApp(config, persist_config=False)

    async with app.run_test(size=(100, 30)) as pilot:
        app._enter_chat_mode()
        chat = app.query_one("#chat-area", VerticalScroll)
        await chat.mount(*(Static(f"background line {index}") for index in range(80)))
        await pilot.pause()
        chat.scroll_end(animate=False, force=True, immediate=True)
        await pilot.pause()
        background_before = chat.scroll_y
        assert background_before > 0

        app._handle_model_command("/model")
        await pilot.pause()
        assert isinstance(app.screen, SelectScreen)
        options = app.screen.query_one("#select-list", OptionList)
        assert options.highlighted == 1

        await pilot.press("up")
        await pilot.pause()
        assert options.highlighted == 0
        assert chat.scroll_y == background_before

        await pilot.press("down")
        await pilot.pause()
        assert options.highlighted == 1
        assert chat.scroll_y == background_before
