# Engram Memory Retrieval Phase 11 Evaluation Examples

Date: 2026-05-25

## Goal
Capture deterministic evidence for semantic debug visibility and FTS fallback safety in:
- `engram start --debug-retrieval`
- `engram memory related-to-task <task-id> --debug`

## Comparison: FTS-only vs semantic-enabled

| Scenario | Setup | Expected debug evidence | Outcome |
|---|---|---|---|
| FTS-only (semantic index missing) | No semantic artifacts under `~/.engram/indexes/<project-id>/semantic` | `semantic_status=missing`, `semantic_fallback_used=True`, `semantic_reason=semantic index missing: ...`, non-zero `fts_returned_candidate_count` when lexical matches exist | FTS remains available; startup/related-to-task do not fail |
| Semantic-enabled (index ready) | Semantic artifacts present and fresh | `semantic_status=ready`, `semantic_fallback_used=False`, non-zero `semantic_returned_candidate_count` for semantic hits | Semantic candidates participate in fusion |
| Semantic stale | Semantic artifacts present but watermark mismatch | `semantic_status=stale`, `semantic_fallback_used=True`, `semantic_reason=semantic index stale: ...` | Retrieval degrades to FTS-only behavior |
| Semantic fallback error | Semantic retrieval failure after readiness check (for example dependency/load failure) | `semantic_status=error`, `semantic_fallback_used=True`, `semantic_reason=semantic retrieval failed: ...` | Retrieval remains resilient; no startup crash |

## Required debug fields verified

- Semantic index freshness/status:
  - `semantic_status`
  - `semantic_fallback_used`
  - `semantic_reason`
- Candidate and fusion counters:
  - `fused_returned_candidate_count`
  - `fts_returned_candidate_count`
  - `semantic_returned_candidate_count`
  - `fused_duplicate_count`
- Budget outcomes:
  - `used_char_count=<used>/<section_char_budget>`
  - `section_budget_exhausted=<bool>`
- Fallback visibility:
  - `fallback reason: ...` when FTS path uses fallback metadata

## Test coverage mapping

- `tests/test_memory_retrieval_startup_orchestration.py`
  - missing, ready, stale, and semantic error/fallback state propagation
- `tests/test_work_cmds.py`
  - `engram start --debug-retrieval` semantic metadata and fusion counters
- `tests/test_memory_cmds_generic.py`
  - `engram memory related-to-task --debug` semantic missing status/counters/budget output
