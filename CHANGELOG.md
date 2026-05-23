# Changelog

## [Unreleased]

- feat(cli): implement `engram phase add` with project-scoped normalized duplicate-title validation and automatic per-project order indexing.
- feat(cli): add shared phase title normalization and project-scoped phase resolver helpers with ambiguity/missing-case coverage.
- feat(cli): add dedicated `engram phase` command group registration plus CLI entrypoint tests for root discovery and `phase --help` loading.
- feat(model): add `get_effective_phase_title` compatibility helper to prefer first-class `Phase.title`, safely fallback to legacy `task.phase`, and return `None` for unphased or stale references.
- feat(model): teach Task create/read/update paths to persist `phase_id` while keeping legacy `phase` callers compatible.
- fix(db): backfill legacy `tasks.phase` values into project-scoped `phases` with idempotent `tasks.phase_id` migration coverage.
- feat(model): add Phase domain model with status validation, project-ordered listing, deterministic order index defaults, and CRUD tests.
- feat(db): add first-class phases schema and idempotent nullable `tasks.phase_id` migration.
- docs: align public README and user manual with the current CLI and remove stale planning docs.
- chore: prepare repository for public release, add MIT license, exclude unpolished UI, and write portfolio README.md
- feat(cli): implement --all/-a option for 'engram task list' and improve empty states with helpful guidance.
- feat(cli): 'engram task list' by default only shows todo tasks.
- feat(cli): display phase for each task in 'engram task list'.
- feat(cli): checkout to a 'misc' branch during 'engram start' for tasks without a phase.
- fix(cli): fix UnicodeEncodeError in engram guide on legacy windows terminal.
- feat(cli): add working tree safety checks to `engram start` preventing dirty state checkouts.
- feat(cli): support dynamic Conventional Commit types and optional `-t`/`--type` flag in `engram finish`.
- feat(cli): implement task dependency status propagation, list/next visualization, and CLI blocker enforcement.
- feat(cli): implement DFS cycle detection for task dependencies to block circular relationships.
- feat(cli): add `depends_on` support to task commands with partial/exact ID resolution.
