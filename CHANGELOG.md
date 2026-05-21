# Changelog

## [Unreleased]

- feat(cli): checkout to a 'misc' branch during 'engram start' for tasks without a phase.
- fix(cli): fix UnicodeEncodeError in engram guide on legacy windows terminal.
- feat(cli): add working tree safety checks to `engram start` preventing dirty state checkouts.
- feat(cli): support dynamic Conventional Commit types and optional `-t`/`--type` flag in `engram finish`.
- feat(cli): implement task dependency status propagation, list/next visualization, and CLI blocker enforcement.
- feat(cli): implement DFS cycle detection for task dependencies to block circular relationships.
- feat(cli): add `depends_on` support to task commands with partial/exact ID resolution.
- fix(ui): fix fatal React crash due to mapping over `task.tags` instead of `task.tag_list`.
- feat(workflow): add Codex workflow reference files.
- fix(ui): make the local UI follow the latest project that launches `engram ui`.
- feat(ui): add live read-only local inspection console.
- fix(ui): keep status pills compact in dashboard cards.
