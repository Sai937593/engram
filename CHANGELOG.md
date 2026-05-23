# Changelog

## [Unreleased]

- feat(cli): support updating task phase association via `phase_id` with project-scoped ID or unique title resolution, clear commands (`none`, `null`, `clear`), and backward-compatible legacy updates.
- fix(cli): display effective phase titles in `engram task get` and `engram task list` using first-class phase lookup with legacy fallback.
- feat(cli): add `engram task list --phase` filtering by first-class phase id/unique title with legacy-only fallback matching and explicit phase_id precedence.
- feat(cli): resolve `engram task add --phase` against first-class project phases by id or unique normalized title, mirror resolved phase titles into legacy task.phase, reject ambiguous/missing phase references, and preserve free-form legacy phase text when no first-class phase match exists.
- fix(cli): route `phase add --status active` and `phase update --field status --value active` through the single-active-phase activation path.
- feat(cli): add `engram phase done` with required evidence, unfinished-linked-task guard for todo/in-progress/blocked statuses, and `--force` override coverage across phase_id plus legacy phase links.
- feat(cli): add `engram phase start` with deterministic single-active-phase enforcement, same-project active-phase demotion, and idempotent activation coverage.
- feat(cli): add `engram phase update` with mutable-field validation, status/order parsing checks, and project-scoped normalized title collision protection.
- feat(cli): add `engram phase get` with shared project-scoped id/title resolution, full phase detail output, and ambiguity/missing lookup coverage.
- feat(cli): add `engram phase list` with project-scoped ordered output and compact phase summary columns plus CLI coverage for empty/single/multi-phase listing.
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
