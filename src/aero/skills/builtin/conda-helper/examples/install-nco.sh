#!/bin/bash
# The agent should normally call ensure_runtime_tools({"tools": ["ncks"]}).
# This standalone example initializes Aero's managed runtime, never user Conda.
set -euo pipefail

aero setup

echo "Runtime initialized. In an agent task, call ensure_runtime_tools for ncks."
~/.aero/runtime/envs/aero-agent/bin/python --version
