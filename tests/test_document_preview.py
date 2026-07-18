"""Tests for opening local documents with the system default application."""

from aero.toolbox.paths import use_workspace
from aero.toolbox.tools import documents


def test_preview_pdf_uses_system_default_viewer(tmp_path, monkeypatch):
    pdf_path = tmp_path / "literature" / "paper.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"%PDF-1.7\n")
    calls = []

    monkeypatch.setattr(documents.sys, "platform", "darwin")
    monkeypatch.setattr(
        documents.subprocess,
        "run",
        lambda args, check: calls.append((args, check)),
    )

    with use_workspace(tmp_path):
        result = documents.preview_pdf("literature/paper.pdf")

    assert result["status"] == "success"
    assert result["file_path"] == "literature/paper.pdf"
    assert calls == [(["open", str(pdf_path)], True)]


def test_preview_pdf_rejects_non_pdf_and_outside_project(tmp_path):
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not a pdf")
    outside = tmp_path.parent / "outside.pdf"
    outside.write_bytes(b"%PDF-1.7\n")

    with use_workspace(tmp_path):
        wrong_type = documents.preview_pdf("notes.txt")
        outside_result = documents.preview_pdf(str(outside))

    assert wrong_type["status"] == "error"
    assert "不是 PDF" in wrong_type["message"]
    assert outside_result["status"] == "error"
    assert "当前项目或实验工作区" in outside_result["message"]
