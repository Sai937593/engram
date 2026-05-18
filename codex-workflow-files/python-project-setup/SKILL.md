---
name: python-project-setup
description: Use when setting up a new Python project or repairing missing baseline project structure. Covers pyproject.toml, src layout, pytest, ruff, .gitignore, .env.example, CHANGELOG.md, README.md, and minimal local development hygiene for Python repos.
---

# Python Project Setup

## Audit the repo first

- Read `pyproject.toml`, `requirements*.txt`, and existing repo files before changing setup.
- Prefer the repo's current stack and add dependencies only for a verified gap.
- Use `uv` for dependency and command execution unless the repo clearly uses something else.

## Apply the baseline

For a new or incomplete Python repo, add or verify:

- `src/<package>/` with package init files
- `tests/` with `conftest.py`
- `pyproject.toml` with project metadata plus `pytest` and `ruff` in dev dependencies
- `.gitignore` covering `.env`, `.venv`, `__pycache__`, build artifacts, local databases, and raw data
- `README.md`
- `CHANGELOG.md` with `## [Unreleased]`
- `.env.example` when the project reads environment variables

## Keep setup conservative

- Prefer `src` layout.
- Put lint and test tools in dev dependencies, not production dependencies.
- Add type annotations to new Python functions.
- Add one-line docstrings to new public interfaces.
- Keep notebooks out of production imports.

## Validate the baseline

Run the repo's existing validation path first. If none exists, use:

```powershell
uv run ruff check . --fix
uv run ruff format .
uv run pytest tests/ -v
```

Only finish when the repo can be installed and the validation path passes.
