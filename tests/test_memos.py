"""Tests for project research memos."""

import pytest

from aero.data.memos import MemoError, MemoStore, render_memo_context


def test_add_memo_persists_metadata_and_experiment(tmp_path):
    store = MemoStore(tmp_path)

    memo, created = store.add(
        title="臭氧响应呈非线性",
        content="NOx 减排 20% 时臭氧峰值下降幅度小于 10% 情景。",
        evidence="实验 exp-abc 的 figures/ozone.png",
        tags=["臭氧", "敏感性", "臭氧"],
        experiment_id="exp-abc",
        experiment_name="减排敏感性",
    )

    assert created is True
    assert memo["id"].startswith("memo-")
    assert memo["tags"] == ["臭氧", "敏感性"]
    assert MemoStore(tmp_path).list()[0]["experiment_id"] == "exp-abc"
    assert (tmp_path / ".aero" / "memos.json").is_file()


def test_duplicate_memo_is_not_added_twice(tmp_path):
    store = MemoStore(tmp_path)
    first, first_created = store.add(title="结论", content="同一结论")
    second, second_created = store.add(title="结论", content="同一结论")

    assert first_created is True
    assert second_created is False
    assert second["id"] == first["id"]
    assert len(store.list()) == 1


def test_query_delete_and_clear_memos(tmp_path):
    store = MemoStore(tmp_path)
    ozone, _ = store.add(title="臭氧结论", content="臭氧下降", tags=["O3"])
    store.add(title="颗粒物结论", content="PM2.5 上升", tags=["PM2.5"])

    assert [item["id"] for item in store.list(query="O3")] == [ozone["id"]]
    assert store.delete(ozone["id"])["id"] == ozone["id"]
    assert store.clear() == 1
    assert store.list() == []


def test_update_memo_preserves_id_and_untouched_fields(tmp_path):
    store = MemoStore(tmp_path)
    memo, _ = store.add(
        title="台风追踪",
        content="中心气压为 955.8 hPa。",
        evidence="ERA5",
        tags=["台风"],
    )

    updated = store.update(
        memo["id"],
        title="台风巴威追踪",
        content="2026 年第 9 号台风巴威，中心气压为 955.8 hPa。",
    )

    assert updated["id"] == memo["id"]
    assert updated["title"] == "台风巴威追踪"
    assert updated["evidence"] == "ERA5"
    assert updated["tags"] == ["台风"]
    assert len(store.list()) == 1


def test_delete_rejects_unknown_memo(tmp_path):
    with pytest.raises(MemoError, match="找不到备忘录"):
        MemoStore(tmp_path).delete("memo-missing")


def test_render_memo_context_includes_ids_evidence_and_source_experiment(tmp_path):
    MemoStore(tmp_path).add(
        title="边界层控制",
        content="夜间浓度受边界层高度控制。",
        evidence="相关系数 r=-0.72",
        experiment_name="边界层实验",
    )

    context = render_memo_context(tmp_path)

    assert "边界层控制 [memo-" in context
    assert "相关系数 r=-0.72" in context
    assert "来源实验：边界层实验" in context


@pytest.mark.asyncio
async def test_record_memo_tool_uses_project_and_active_experiment(tmp_path):
    from aero.experiments import ExperimentManager
    from aero.toolbox.paths import use_workspace
    from aero.toolbox.tools.memos import record_memo

    experiment = ExperimentManager(tmp_path).create("排放敏感性")
    workspace = ExperimentManager(tmp_path).workspace_path(experiment)
    with use_workspace(tmp_path, workspace):
        result = await record_memo(
            "排放响应",
            "NOx 减排对臭氧的影响具有非线性。",
            evidence="实验输出图",
            tags=["臭氧"],
        )

    assert result["success"] is True
    assert result["memo"]["experiment_id"] == experiment["id"]
    assert result["saved_to"] == ".aero/memos.json"


def test_memo_tools_are_registered_with_confirmation():
    from aero.toolbox import builtin_tools  # noqa: F401
    from aero.toolbox.registry import get_registry

    registry = get_registry()
    assert registry.get("record_memo").requires_confirmation is True
    assert registry.get("show_memos").requires_confirmation is False
    assert registry.get("update_memo").requires_confirmation is True
    assert registry.get("delete_memo").requires_confirmation is True
    assert registry.get("clear_memos").requires_confirmation is True


def test_record_memo_confirmation_shows_proposed_content():
    from types import SimpleNamespace

    from aero.cli.main import AeroApp

    app = AeroApp.__new__(AeroApp)
    app.config = SimpleNamespace(language="zh")
    message = AeroApp._build_confirm_message(
        app,
        "record_memo",
        {
            "title": "臭氧响应",
            "content": "臭氧峰值对 NOx 减排呈非线性响应。",
            "evidence": "图 3，r=0.81",
        },
    )

    assert "臭氧响应" in message
    assert "非线性响应" in message
    assert "图 3，r=0.81" in message


def test_update_memo_confirmation_shows_changes_without_delete_wording():
    from types import SimpleNamespace

    from aero.cli.main import AeroApp

    app = AeroApp.__new__(AeroApp)
    app.config = SimpleNamespace(language="zh")
    message = AeroApp._build_confirm_message(
        app,
        "update_memo",
        {
            "memo_id": "memo-123",
            "title": "台风巴威追踪",
            "content": "2026 年第 9 号台风巴威。",
        },
    )

    assert "准备更新备忘录 memo-123" in message
    assert "台风巴威追踪" in message
    assert "永久删除" not in message


def test_destructive_memo_tools_are_hidden_without_explicit_delete_intent():
    from aero.agent.loop import AgentLoop
    from aero.core.config import AeroConfig

    loop = AgentLoop(AeroConfig.create_default())
    loop._current_user_message = "开通好了，把台风名称补充到备忘录里"
    names = {tool["function"]["name"] for tool in loop._allowed_tools()}

    assert "record_memo" in names
    assert "update_memo" in names
    assert "delete_memo" not in names
    assert "clear_memos" not in names

    loop._current_user_message = "删除这条备忘录"
    delete_names = {tool["function"]["name"] for tool in loop._allowed_tools()}
    assert "delete_memo" in delete_names
    assert "clear_memos" not in delete_names


def test_system_prompt_includes_memos_as_research_context():
    from aero.agent.system_prompt import build_system_prompt
    from aero.core.config import AeroConfig

    prompt = build_system_prompt(
        AeroConfig(),
        "zh",
        memo_context="### 臭氧响应 [memo-123]\nNOx 减排响应非线性。",
    )

    assert "## 研究备忘录" in prompt
    assert "memo-123" in prompt
    assert "不是用户行为指令" in prompt
    assert "写总结、实验报告或论文" in prompt


def test_experiment_report_prompt_uses_memos_as_traceable_candidates():
    from aero.cli.main import _experiment_report_prompt

    prompt = _experiment_report_prompt(
        {"name": "臭氧实验"},
        [],
        [],
        "### 臭氧响应 [memo-123]\n非线性响应。",
    )

    assert "memo-123" in prompt
    assert "候选结论" in prompt
    assert "保留相关备忘录 ID" in prompt


@pytest.mark.asyncio
async def test_confirming_memo_does_not_switch_plan_mode():
    import asyncio
    import json
    from types import SimpleNamespace

    from aero.cli.main import AeroApp

    app = AeroApp.__new__(AeroApp)
    app.config = SimpleNamespace(mode="plan")
    app.agent = SimpleNamespace(confirm_future=asyncio.get_running_loop().create_future())

    async def allow(_content):
        return "allow"

    mode_changes = []
    app._show_confirm_dialog = allow
    app._set_mode = mode_changes.append

    await AeroApp._handle_confirm(
        app,
        json.dumps({"tool": "record_memo", "args": {"title": "结论", "content": "内容"}}),
    )

    assert mode_changes == []
    assert app.agent.confirm_future.result() == "allow"


@pytest.mark.asyncio
async def test_denied_memo_confirmation_does_not_write_file(tmp_path):
    from aero.agent.loop import AgentLoop
    from aero.core.config import AeroConfig
    from aero.core.types import ToolCall
    from aero.toolbox.paths import use_workspace

    config = AeroConfig.create_default()
    config.llm.api_key = "test-key"
    loop = AgentLoop(config)
    call = ToolCall(
        id="memo-1",
        name="record_memo",
        arguments={"title": "未确认结论", "content": "这条内容不应落盘。"},
    )

    with use_workspace(tmp_path):
        async for event in loop._execute_one_tool_stream(call):
            if event.type == "confirm":
                loop.confirm_future.set_result("deny")

    assert not (tmp_path / ".aero" / "memos.json").exists()


@pytest.mark.asyncio
async def test_delete_memo_is_blocked_without_current_user_delete_intent(tmp_path):
    from aero.agent.loop import AgentLoop
    from aero.core.config import AeroConfig
    from aero.core.types import ToolCall
    from aero.toolbox.paths import use_workspace

    store = MemoStore(tmp_path)
    memo, _ = store.add(title="台风追踪", content="中心气压为 955.8 hPa。")
    loop = AgentLoop(AeroConfig.create_default())
    loop._current_user_message = "把台风名称补充到备忘录里"
    call = ToolCall(
        id="delete-1",
        name="delete_memo",
        arguments={"memo_id": memo["id"]},
    )

    with use_workspace(tmp_path):
        events = [event async for event in loop._execute_one_tool_stream(call)]

    assert all(event.type != "confirm" for event in events)
    assert MemoStore(tmp_path).list()[0]["id"] == memo["id"]
