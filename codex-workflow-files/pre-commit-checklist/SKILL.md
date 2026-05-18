---
name: pre-commit-checklist
description: Use before committing changes in a Python repository. Trigger on requests to do a final check, prepare a commit, run pre-commit validation, or confirm a change is ready to push. Covers linting, formatting, tests, secret checks, changelog updates, and commit hygiene.
---

# Pre-Commit Checklist

## Inspect the repo gate

- Read the repo's configured validation path before inventing one.
- If `.pre-commit-config.yaml` exists, prefer the configured hooks.
- If the repo has a task tracker or session workflow, complete the commit only after code validation succeeds.

## Run the quality checks

Use the repo's standard commands first. If the repo has no explicit path, use:

```powershell
uv run ruff check . --fix
uv run ruff format .
uv run pytest tests/ -v
```

If tests or validation fail twice, stop and mark the task blocked instead of looping.

## Scan for accidental secrets

Check staged changes for:

- API keys
- passwords
- tokens
- `.env` files
- copied credentials in docs or examples

Move secrets to `.env` or `.env.example` as appropriate, then unstage the sensitive file.

## Verify release hygiene

Before committing:

- Update `CHANGELOG.md` for `feat` and `fix` commits.
- Update `README.md` when installation, configuration, or behavior changed.
- Keep the commit message conventional and scoped.
- Stage only files that belong to the current task.

## Close cleanly

Record the validation evidence that supports the commit, then push only after the repo's checks pass.
