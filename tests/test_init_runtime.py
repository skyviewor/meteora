"""Tests for Aero's private Micromamba runtime."""

import io
import subprocess
import tarfile
from pathlib import Path

from aero.cli import init_runtime


def completed(command: list[str], returncode: int = 0, stdout: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")


def configure_runtime(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "aero-home" / "runtime"
    micromamba = root / "bin" / "micromamba"
    env = root / "envs" / "aero-agent"
    monkeypatch.setenv("AERO_RUNTIME_ROOT", str(root))
    return root, micromamba, env


def test_setup_runtime_creates_private_python_312_environment(monkeypatch, tmp_path):
    root, micromamba, env = configure_runtime(monkeypatch, tmp_path)
    micromamba.parent.mkdir(parents=True)
    micromamba.write_text("")
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int):
        calls.append(command)
        (env / "bin").mkdir(parents=True, exist_ok=True)
        (env / "bin" / "python").write_text("")
        return completed(command)

    monkeypatch.setattr(init_runtime, "_run", fake_run)

    assert init_runtime.setup_runtime() is True
    assert calls[0][:3] == [str(micromamba), "create", "--yes"]
    assert ["--root-prefix", str(root)] == calls[0][3:5]
    assert ["--prefix", str(env)] == calls[0][5:7]
    assert "python=3.12" in calls[0]


def test_setup_runtime_full_installs_conda_then_pip_packages(monkeypatch, tmp_path):
    root, micromamba, env = configure_runtime(monkeypatch, tmp_path)
    micromamba.parent.mkdir(parents=True)
    micromamba.write_text("")
    (env / "bin").mkdir(parents=True)
    (env / "bin" / "python").write_text("")
    (env / "bin" / "mplfonts").write_text("")
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, timeout: int):
        calls.append(command)
        return completed(command)

    monkeypatch.setattr(init_runtime, "_run", fake_run)

    assert init_runtime.setup_runtime(full=True) is True
    assert calls[0][:3] == [str(micromamba), "env", "update"]
    assert str(init_runtime.CONDA_ENVIRONMENT_FILE) in calls[0]
    assert calls[1][:4] == [str(env / "bin" / "python"), "-m", "pip", "install"]
    assert str(init_runtime.PIP_REQUIREMENTS_FILE) in calls[1]
    assert calls[2][-1] == "init"
    assert calls[3][-1] == "updaterc"


def test_ensure_micromamba_extracts_managed_binary(monkeypatch, tmp_path):
    _root, micromamba, _env = configure_runtime(monkeypatch, tmp_path)

    def fake_urlretrieve(_url: str, destination: Path):
        payload = b"#!/bin/sh\n"
        with tarfile.open(destination, "w:bz2") as archive:
            info = tarfile.TarInfo("bin/micromamba")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    monkeypatch.setattr(init_runtime.urllib.request, "urlretrieve", fake_urlretrieve)

    assert init_runtime.ensure_micromamba() == micromamba
    assert micromamba.read_bytes() == b"#!/bin/sh\n"
    assert micromamba.stat().st_mode & 0o111


def test_clean_runtime_only_removes_private_runtime(monkeypatch, tmp_path):
    root, _micromamba, _env = configure_runtime(monkeypatch, tmp_path)
    project = tmp_path / "project"
    (root / "envs").mkdir(parents=True)
    project.mkdir()
    (project / "aero.yaml").write_text("output: {}\n")

    assert init_runtime.clean_runtime(assume_yes=True) is True
    assert not root.exists()
    assert (project / "aero.yaml").exists()


def test_runtime_diagnostics_requires_python_312(monkeypatch, tmp_path):
    _root, micromamba, env = configure_runtime(monkeypatch, tmp_path)
    micromamba.parent.mkdir(parents=True)
    micromamba.write_text("")
    (env / "bin").mkdir(parents=True)
    (env / "bin" / "python").write_text("")
    monkeypatch.setattr(
        init_runtime,
        "_run",
        lambda command, timeout: completed(command, stdout="3.12.9\n"),
    )

    healthy, checks = init_runtime.runtime_diagnostics()

    assert healthy is True
    assert checks[-1] == ("Python 版本", True, "3.12.9")


def test_common_package_files_keep_cnmaps_pip_only():
    assert "python=3.12" in init_runtime._conda_packages()
    assert "cnmaps" not in init_runtime._conda_packages()
    assert init_runtime._pip_packages() == ("mplfonts", "cnmaps")


def test_conda_helper_documents_python_312_and_pip_only_cnmaps():
    skill_text = Path("src/aero/skills/builtin/conda-helper/SKILL.md").read_text()
    assert "python=3.12" in skill_text
    assert "`cnmaps` is pip-only" in skill_text
    assert "Never install `cnmaps` with conda or mamba" in skill_text
