import pytest

from aero.agent.checkpoint_context import use_checkpoint_creator
from aero.toolbox.tools.checkpoints import (
    compare_checkpoint,
    create_checkpoint,
    list_checkpoints,
    rename_checkpoint,
    start_checkpoint_experiment,
)


@pytest.mark.asyncio
async def test_create_checkpoint_tool_uses_active_chat_context():
    captured = []

    def creator(name):
        captured.append(name)
        return {
            "id": "checkpoint-1",
            "name": name,
            "created_at": 1.0,
            "files": [
                {"path": "script.py", "restore": "exact"},
                {"path": "data/input.nc", "restore": "reference"},
            ],
            "exact_restore": True,
        }

    with use_checkpoint_creator(creator):
        result = await create_checkpoint("before analysis")

    assert captured == ["before analysis"]
    assert result["success"] is True
    assert result["exact_files"] == 1
    assert result["data_references"] == 1


@pytest.mark.asyncio
async def test_checkpoint_query_tools_use_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.md").write_text("first\n")
    from aero.checkpoints import CheckpointManager

    checkpoint = CheckpointManager(tmp_path).create("base")
    (tmp_path / "notes.md").write_text("second\n")

    listed = await list_checkpoints()
    compared = await compare_checkpoint(checkpoint["id"])
    experiment = await start_checkpoint_experiment("trial")

    assert listed["checkpoints"][0]["id"] == checkpoint["id"]
    assert "experiment" not in listed["checkpoints"][0]
    assert "exact_restore" not in listed["checkpoints"][0]
    assert compared["modified"] == ["notes.md"]
    assert experiment["name"] == "trial"
    workspace = tmp_path / experiment["workspace"]
    assert workspace.is_dir()
    for directory in ("scripts", "figures", "plans", "outputs", "reports", "data"):
        assert (workspace / directory).is_dir()


@pytest.mark.asyncio
async def test_checkpoint_list_hides_recovery_protection_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.md").write_text("first\n")
    from aero.checkpoints import CheckpointManager

    manager = CheckpointManager(tmp_path)
    manual = manager.create("manual")
    manager.create("automatic safety", kind="pre-restore")

    default_result = await list_checkpoints()
    all_result = await list_checkpoints(include_safety=True)

    assert [item["id"] for item in default_result["checkpoints"]] == [manual["id"]]
    assert default_result["hidden_safety_count"] == 1
    assert len(all_result["checkpoints"]) == 2
    assert any(item["recovery_protection"] for item in all_result["checkpoints"])


@pytest.mark.asyncio
async def test_rename_checkpoint_tool_updates_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.md").write_text("first\n")
    from aero.checkpoints import CheckpointManager

    checkpoint = CheckpointManager(tmp_path).create("before")

    result = await rename_checkpoint(checkpoint["id"], "after")

    assert result == {
        "success": True,
        "checkpoint_id": checkpoint["id"],
        "name": "after",
    }
    assert CheckpointManager(tmp_path).load(checkpoint["id"])["name"] == "after"
