# PROJECT PLAN — Engram

## Roadmap

### Phase 1: Foundation (DONE)
- [x] pyproject.toml + package scaffold
- [x] ~/.engram/ init + SQLite schema creation
- [x] engram init (repo path binding + project creation)
- [x] engram project CRUD

### Phase 2: Core Entities (DONE)
- [x] engram task CRUD + status lifecycle
- [x] engram memory CRUD + type/tag/scope/always_include
- [x] Field-level updates (--field --value) + audit log

### Phase 3: Sessions & Context (DONE)
- [x] engram session start / close (embedded checkpoint)
- [x] engram context startup (< 500 token target)
- [x] engram context task

### Phase 4: Search (DONE)
- [x] FTS5 virtual table + sync triggers on memories
- [x] engram memory search (text + type + tag filters)

### Phase 5: Exports & Polish (DONE)
- [x] engram export snapshot
- [x] engram export handoff
- [x] Error handling, validation, edge cases
- [x] CLI table formatting refinements

### Phase 6: Demo & Validation (DONE)
- [x] End-to-end demo scenario (acceptance test)
