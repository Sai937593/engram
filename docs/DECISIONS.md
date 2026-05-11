# DECISIONS

## Architectural Decisions

| Date | Decision | Choice | Rationale |
|:-----|:---------|:-------|:----------|
| 2026-05-11 | Storage Backend | **SQLite** | Queryable, zero-config (stdlib), performant for scoped memory. |
| 2026-05-11 | Storage Location | **Global (~/.engram/)** | Survives repo moves/deletes, enables cross-project search, zero repo pollution. |
| 2026-05-11 | Primary Interface | **CLI** | Universal compatibility for agents, scriptable, low overhead. |
| 2026-05-11 | Context Strategy | **On-demand** | Minimize token usage by allowing agents to pull specific memories/tasks as needed. |
| 2026-05-11 | Entity Model | **4 Tables** | Simplified from 9 to Project, Task, Memory, Session for MVP speed. |
| 2026-05-12 | Toolchain | **uv** | Used for package management and installation instead of pip for speed. |
