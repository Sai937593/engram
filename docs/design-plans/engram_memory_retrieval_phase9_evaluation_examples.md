# Engram Memory Retrieval Phase 9 Evaluation Examples

Date: 2026-05-24

## Scope and Method

- Evaluated current FTS-first behavior only (no code or ranking changes).
- Collected evidence with:
  - `engram memory related-to-task <task-id> --debug`
  - `uv run python` script calling `build_task_retrieval_query`, `retrieve_task_memory_candidates`, and `pack_task_memories` to compare candidate vs selected IDs.

## Observed Defaults (Current Behavior)

- `max_candidates=20`
- `selected_item_count=6` in all sampled runs (preferred-K cap)
- `section_char_budget=3600`
- Observed `used_char_count` range: `1428-1687`
- `section_budget_exhausted=False` in all sampled runs

Interpretation: hidden items in this sample are caused by preferred-K selection, not by section budget pressure.

## Evaluated Examples

| Task | Expected Useful Memories | Actual Selected Memories (IDs) | Misses | False Positives | Notes |
| --- | --- | --- | --- | --- | --- |
| `e393ba59` Harden FTS retrieval fallback behavior | `d04ae2d0` (degrade on FTS errors), `724c7520` (FTS query normalization), `68c96849` (orchestration failure isolation) | `d04ae2d0, 724c7520, 12201a9b, 89e01e6c, 94e3bb20, 68c96849` | No critical miss in selected set | `94e3bb20` is tangential | Good precision for a retrieval-focused task. |
| `87c007fb` Add startup retrieval fallback and timeout safeguards | `12201a9b` (timeout fallback), `68c96849` (orchestration isolation), `d04ae2d0` (FTS error degrade) | `12201a9b, d04ae2d0, 68c96849, 94e3bb20, 6a36b1d1, 89e01e6c` | No critical miss in selected set | `89e01e6c` and `94e3bb20` are weaker matches | Strong recall for directly-related failure-handling memories. |
| `d38e82a7` Expose optional debug retrieval output on engram start | `a13441f1` (candidate ordering), `722ddc19` (pack metadata), `94e3bb20` (query metadata) | `722ddc19, 94e3bb20, d04ae2d0, 12201a9b, 89e01e6c, 95309707` | `a13441f1` was a hidden candidate (not selected) | `95309707` is weaker than hidden `a13441f1` for this task | Preferred-K cap can hide still-useful candidates. |
| `bd084dcc` Add debug diagnostics for related-to-task | `a13441f1` (ordering), `722ddc19` (pack metadata), `89e01e6c` (query builder contract) | `a13441f1, d04ae2d0, 94e3bb20, 12201a9b, aa58206f, 722ddc19` | `89e01e6c` was hidden | `aa58206f` is less directly related | Similar preferred-K tradeoff: one relevant candidate hidden. |
| `03dc756d` Create User Manual | `9ea05d4b` (public docs must match CLI help) | `6a36b1d1, a13441f1, d04ae2d0, 724c7520, 0d8df984, a9be58fa` | `9ea05d4b` not retrieved (project-scope memory) | Most selected memories are retrieval internals, not docs-focused | Clear miss + precision failure outside retrieval domain. |
| `b0e3e917` Implement Exports | `2c62738c` (Export Philosophy decision) | `6a36b1d1, d04ae2d0, 64e58aa2, c672f016, a13441f1, 722ddc19` | `2c62738c` not retrieved (project-scope memory) | Most selected memories are retrieval internals | Another clear scope mismatch for non-retrieval tasks. |
| `5dd7abc5` Prepare repository for public release | `9ea05d4b` (public docs must match CLI help) | `d04ae2d0, 724c7520, 0d8df984, 89e01e6c, 722ddc19, 95309707` | `9ea05d4b` not retrieved (project-scope memory) | All selected memories are weak for release-readiness work | Precision degrades when task vocabulary overlaps generic engineering terms. |

## Observed Failure Modes from Examples

1. **Scope gap:** task-memory retrieval excludes project-scope memories, causing misses for tasks that mostly depend on project-level lessons/decisions.
2. **Generic-term lexical drift:** terms like "task", "debug", "output", "tests", and "query" pull retrieval-internal memories into unrelated tasks.
3. **Preferred-K truncation of relevant candidates:** with many near-matches, at least one relevant candidate can be hidden at `selected_item_count=6`.

## K and Budget Validation (Current Evidence)

- Current packing budget (`3600`) is not the limiting factor in sampled runs.
- Current selected count (`6`) is adequate for retrieval-heavy tasks, but often too permissive for non-retrieval tasks because irrelevant memories still fill all slots.
- Evidence supports carrying these defaults into the next tuning task, with targeted follow-up on relevance thresholds/scope strategy rather than budget expansion.
