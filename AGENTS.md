# Repository Guidelines

## Project Structure & Module Organization

Aerolytica is a Python 3.12+ package using a `src/` layout. Application code lives in
`src/aero/`: `agent/` contains orchestration and LLM clients, `adapters/` integrates
weather-data services, `cli/` implements the command line and Textual UI, `core/` holds
shared configuration, `datasets/` defines providers, and `toolbox/` exposes agent tools.
Built-in workflows belong under `src/aero/skills/builtin/`. Tests live in `tests/`,
documentation in `docs/`, plans in `plans/`, release helpers in `scripts/`, and the static
site in `website/`.

## Build, Test, and Development Commands

- `uv sync --extra dev` — create/update the development environment.
- `uv run aero chat` — run the local CLI from the checked-out source.
- `uv run pytest` — run the complete test suite.
- `uv run pytest tests/test_config.py -v` — run one focused test module.
- `uv run ruff check src tests` — check imports, style, and common errors.
- `uv run ruff format src tests` — format Python sources.
- `uv build` — produce source and wheel distributions through Hatchling.

Equivalent Pixi tasks include `pixi run test`, `pixi run lint`, and `pixi run fmt`.

## Coding Style & Naming Conventions

Use four-space indentation, type hints for public interfaces, and a maximum line length
of 100 characters. Ruff targets Python 3.12 and enforces `E`, `F`, `I`, `N`, and `W`
rules. Use `snake_case` for modules and functions, `PascalCase` for classes, and
`UPPER_SNAKE_CASE` for constants. Keep provider-specific logic in adapters or providers.

## Testing Guidelines

Pytest uses automatic asyncio support and a 60-second per-test timeout. Name files
`test_<area>.py` and tests `test_<behavior>`. Add regression coverage with every bug fix,
and mock network calls, credentials, downloads, and external model services. Run the
focused tests while developing, then the full suite and Ruff before submitting.

## Commit & Pull Request Guidelines

Prefer concise, imperative Conventional Commit-style subjects such as `feat: add ...`,
`fix: validate ...`, `docs: update ...`, `refactor: simplify ...`, or `chore: ...`.
Reserve `WIP:` for temporary branch commits and clean it up before merge. Pull requests
should explain motivation and user-visible effects, link relevant issues, list validation
commands, and call out configuration or dependency changes. Include terminal output or
screenshots for CLI, TUI, plotting, or website changes.

## Security & Configuration

Never commit API keys, downloaded research data, or `~/.aero/secrets.yaml`. Use project
configuration templates such as `templates/project/aero.yaml`, and keep tests independent
of locally configured credentials and runtimes.
