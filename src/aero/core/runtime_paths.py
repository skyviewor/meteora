"""Paths for Aero's private scientific runtime."""

from __future__ import annotations

import os
from pathlib import Path


def aero_home() -> Path:
    """Return Aero's user data directory."""
    return Path(os.environ.get("AERO_HOME", "~/.aero")).expanduser()


def runtime_root() -> Path:
    """Return the root owned exclusively by Aero's Micromamba runtime."""
    configured = os.environ.get("AERO_RUNTIME_ROOT")
    return Path(configured).expanduser() if configured else aero_home() / "runtime"


def micromamba_path() -> Path:
    """Return the managed Micromamba executable path."""
    configured = os.environ.get("AERO_MICROMAMBA")
    return Path(configured).expanduser() if configured else runtime_root() / "bin" / "micromamba"


def runtime_env_path() -> Path:
    """Return the fixed prefix for the aero-agent environment."""
    configured = os.environ.get("AERO_RUNTIME_ENV")
    return Path(configured).expanduser() if configured else runtime_root() / "envs" / "aero-agent"


def runtime_bin_path() -> Path:
    return runtime_env_path() / ("Scripts" if os.name == "nt" else "bin")


def runtime_python_path() -> Path:
    return runtime_bin_path() / ("python.exe" if os.name == "nt" else "python")
