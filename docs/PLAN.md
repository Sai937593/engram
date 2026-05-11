# PROJECT PLAN — Engram

## Roadmap

### Phase 1: Foundation (DONE)
- [x] pyproject.toml + package scaffold
- [x] ~/.engram/ init + SQLite schema creation
- [x] engram init (repo path binding + project creation)
- [x] engram project CRUD

### Phase 2: Core Entities (NEXT)

### Phase 2: Core Entities
- [ ] engram task CRUD + status lifecycle
- [ ] engram memory CRUD + type/tag/scope/always_include
- [ ] Field-level updates (--field --value) + audit log

### Phase 3: Sessions & Context
- [ ] engram session start / close (embedded checkpoint)
- [ ] engram context startup (< 500 token target)
- [ ] engram context task

### Phase 4: Search
- [ ] FTS5 virtual table + sync triggers on memories
- [ ] engram memory search (text + type + tag filters)

### Phase 5: Exports & Polish
- [ ] engram export snapshot
- [ ] engram export handoff
- [ ] Error handling, validation, edge cases

### Phase 6: Demo & Validation
- [ ] End-to-end demo scenario (acceptance test)
