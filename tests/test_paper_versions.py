"""Tests for single-document paper version history."""

import pytest

from aero.paper_versions import PaperVersionError, PaperVersionManager


def test_paper_versions_save_diff_and_restore_only_bound_document(tmp_path):
    paper = tmp_path / "paper" / "main.md"
    other = tmp_path / "notes.md"
    paper.parent.mkdir()
    paper.write_text("# Title\n\nFirst result.\n")
    other.write_text("keep me\n")
    manager = PaperVersionManager(tmp_path)

    initialized = manager.initialize()
    first_id = initialized["head"]
    paper.write_text("# Title\n\nUpdated result.\nNew line.\n")
    second = manager.save("Updated results")

    assert second["created"] is True
    assert second["parent_id"] == first_id
    assert len(manager.list()) == 2
    assert manager.status()["changed"] is False

    paper.write_text("# Title\n\nWorking change.\n")
    diff = manager.diff(second["id"])
    assert diff.changed is True
    assert diff.added_lines == 1
    assert diff.removed_lines == 2
    assert "+Working change." in diff.unified_diff

    restored = manager.restore(first_id)

    assert paper.read_text() == "# Title\n\nFirst result.\n"
    assert other.read_text() == "keep me\n"
    assert restored["protection_version"]["kind"] == "pre-restore"
    assert manager.status()["head"]["id"] == first_id


def test_paper_versions_do_not_duplicate_unchanged_content(tmp_path):
    paper = tmp_path / "paper" / "main.md"
    paper.parent.mkdir()
    paper.write_text("same\n")
    manager = PaperVersionManager(tmp_path)
    manager.initialize()

    unchanged = manager.save("duplicate")

    assert unchanged["created"] is False
    assert len(manager.list()) == 1


def test_paper_versions_initialize_creates_fixed_main_document(tmp_path):
    manager = PaperVersionManager(tmp_path)

    initialized = manager.initialize()

    assert initialized["document"] == "paper/main.md"
    assert initialized["document_created"] is True
    assert (tmp_path / "paper" / "main.md").read_text() == ""

    repeated = manager.initialize()
    assert repeated["created"] is False
    assert repeated["head"] == initialized["head"]


def test_paper_versions_reject_path_outside_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n")

    with pytest.raises(PaperVersionError, match="paper/main.md"):
        PaperVersionManager(project)._safe_document_path(outside)


def test_paper_versions_reject_markdown_outside_paper_directory(tmp_path):
    outside = tmp_path / "notes.md"
    outside.write_text("outside\n")

    with pytest.raises(PaperVersionError, match="paper/main.md"):
        PaperVersionManager(tmp_path)._safe_document_path(outside)


def test_paper_versions_reject_other_markdown_inside_paper_directory(tmp_path):
    with pytest.raises(PaperVersionError, match="paper/main.md"):
        PaperVersionManager(tmp_path)._safe_document_path("other.md")
