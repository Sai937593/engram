# Implementation Plan - Task aa4e1f93

## Scope
Add or update focused regression tests for simplified phase-2 task model behavior only: creation validation, migration/compatibility handling, open-queue workflow start selection, and `is_verified` default/invalidation semantics. Keep phase-4 verify staging and phase-5 finish-and-commit semantics out of scope except preserving compatibility with existing entry points.

## Target Files
- tests/test_db.py
- tests/test_task.py
- tests/test_services_task.py
- tests/test_services_workflow_start_basic.py
- tests/test_services_workflow_start_dirty.py
- tests/test_services_workflow_start_resume.py
- tests/test_services_workflow_start_context.py

## Steps
1. Review current assertions in the listed test files and identify gaps against the task acceptance criteria.
2. Add/adjust tests to prove invalid task creation does not persist any row and returns detailed validation guidance.
3. Add/adjust tests to prove new tasks start as `open` and `is_verified=False` by default.
4. Add/adjust tests to prove workflow start selects from the `open` actionable queue and handles legacy status compatibility intentionally.
5. Add/adjust tests for migration/compatibility paths around legacy statuses and `is_verified` invalidation triggers.
6. Run narrow pytest slices for only changed files first; expand only if failures indicate cross-file coupling.
7. Run `engram_workflow_verify`; fix failures and rerun until passing.
8. Record memory review outcome (`no_change` unless durable memory is produced) and run `engram_workflow_finish`.

## Constraints
- Keep changes test-focused and inside task scope.
- Preserve existing behavior except where simplified phase-2 behavior is explicitly expected.
- Do not edit `planning/`, `workflow/`, or `.github/`.
