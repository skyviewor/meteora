import subprocess
from pathlib import Path

import pytest

from aero.checkpoints import (
    CheckpointError,
    CheckpointManager,
    checkpoint_progress_label,
)


def test_checkpoint_restores_controlled_files_without_touching_user_git(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
    user_head = project / ".git" / "HEAD"
    user_head.write_text("ref: refs/heads/main\n")
    script = project / "scripts" / "plot.py"
    script.parent.mkdir()
    script.write_text("print('first')\n")
    data = project / "data" / "sample.nc"
    data.parent.mkdir()
    data.write_bytes(b"CDF-data-v1")

    manager = CheckpointManager(project)
    checkpoint = manager.create("baseline", session_snapshot=b"encrypted")
    script.write_text("print('second')\n")
    data.write_bytes(b"CDF-data-v2")
    added = project / "notes.md"
    added.write_text("later\n")

    diff = manager.diff(checkpoint["id"])
    assert diff.modified == ("scripts/plot.py",)
    assert diff.added == ("notes.md",)
    assert diff.references_changed == ("data/sample.nc",)

    manager.restore(checkpoint["id"])

    assert script.read_text() == "print('first')\n"
    assert data.read_bytes() == b"CDF-data-v2"
    assert not added.exists()
    assert user_head.read_text() == "ref: refs/heads/main\n"
    assert manager.session_snapshot(checkpoint["id"]) == b"encrypted"
    assert manager._read_state()["experiment"] == "恢复自「baseline」"


def test_checkpoint_does_not_copy_referenced_data(tmp_path):
    project = tmp_path / "project"
    data = project / "data" / "large.grib2"
    data.parent.mkdir(parents=True)
    data.write_bytes(b"GRIB" * 1024)

    manager = CheckpointManager(project)
    checkpoint = manager.create("data reference")

    entry = next(item for item in checkpoint["files"] if item["path"] == "data/large.grib2")
    assert entry["restore"] == "reference"
    assert not list((project / ".aero" / "checkpoints" / checkpoint["id"]).glob("*.grib2"))


def test_checkpoint_excludes_secret_files_from_manifest_and_history(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "secrets.yaml").write_text("api_key: do-not-store\n")
    (project / ".env").write_text("TOKEN=do-not-store\n")
    (project / "aero.yaml").write_text("language: zh\n")

    checkpoint = CheckpointManager(project).create("safe")

    paths = {item["path"] for item in checkpoint["files"]}
    assert "aero.yaml" in paths
    assert "secrets.yaml" not in paths
    assert ".env" not in paths


def test_checkpoint_degrades_when_git_is_unavailable(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "notes.md").write_text("hello\n")
    manager = CheckpointManager(project, git_binary="definitely-not-a-git-binary")

    checkpoint = manager.create("manifest only")

    assert checkpoint["exact_restore"] is False
    assert checkpoint["commit"] is None
    with pytest.raises(CheckpointError, match="没有可用的文件快照"):
        manager.restore(checkpoint["id"])


def test_start_experiment_tracks_current_checkpoint_as_base(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    manager = CheckpointManager(project)
    checkpoint = manager.create("base")

    state = manager.start_experiment("ozone sensitivity")

    assert state["experiment"] == "ozone sensitivity"
    assert state["experiment_base"] == checkpoint["id"]


def test_delete_checkpoint_repairs_children_and_current_pointer(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    notes = project / "notes.md"
    manager = CheckpointManager(project)

    notes.write_text("one\n")
    first = manager.create("first")
    notes.write_text("two\n")
    middle = manager.create("middle")
    notes.write_text("three\n")
    last = manager.create("last")

    deleted_middle = manager.delete(middle["id"])
    reloaded_last = manager.load(last["id"])

    assert deleted_middle["id"] == middle["id"]
    assert manager.load(middle["id"]) is None
    assert reloaded_last["parent_id"] == first["id"]
    assert manager._read_state()["current_checkpoint"] == last["id"]

    manager.delete(last["id"])

    assert manager._read_state()["current_checkpoint"] == first["id"]
    notes.write_text("changed\n")
    manager.restore(first["id"])
    assert notes.read_text() == "one\n"


def test_delete_checkpoint_removes_session_snapshot_and_private_ref(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "notes.md").write_text("content\n")
    manager = CheckpointManager(project)
    checkpoint = manager.create("with session", session_snapshot=b"encrypted")

    manager.delete(checkpoint["id"])

    assert not (manager.checkpoints_dir / checkpoint["id"]).exists()
    assert manager.session_snapshot(checkpoint["id"]) is None
    result = subprocess.run(
        [
            "git",
            f"--git-dir={manager.history_dir}",
            "show-ref",
            "--verify",
            f"refs/checkpoints/{checkpoint['id']}",
        ],
        capture_output=True,
    )
    assert result.returncode != 0


def test_rename_checkpoint_only_updates_its_name(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "notes.md").write_text("content\n")
    manager = CheckpointManager(project)
    checkpoint = manager.create("old name", session_snapshot=b"encrypted")

    renamed = manager.rename(checkpoint["id"], "  new analysis name  ")

    assert renamed["name"] == "new analysis name"
    assert renamed["id"] == checkpoint["id"]
    assert renamed["commit"] == checkpoint["commit"]
    assert renamed["parent_id"] == checkpoint["parent_id"]
    assert renamed["created_at"] == checkpoint["created_at"]
    assert manager.session_snapshot(checkpoint["id"]) == b"encrypted"
    assert manager.load(checkpoint["id"])["name"] == "new analysis name"


def test_rename_checkpoint_rejects_empty_name(tmp_path):
    manager = CheckpointManager(tmp_path)
    checkpoint = manager.create("original")

    with pytest.raises(CheckpointError, match="名称不能为空"):
        manager.rename(checkpoint["id"], "   ")


def test_checkpoint_progress_labels_hide_internal_state_names():
    assert checkpoint_progress_label({"experiment": "main"}) == ""
    assert checkpoint_progress_label({"experiment": "restore-20260716"}) == "恢复后的进度"
    assert checkpoint_progress_label({"experiment": "臭氧敏感性"}) == "实验：臭氧敏感性"
    assert (
        checkpoint_progress_label({"experiment": "恢复自「第二版」"})
        == "恢复自「第二版」"
    )
