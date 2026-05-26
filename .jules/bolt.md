## 2026-05-26 - Database Indexing and Scoping
**Learning:** Project-scoped queries in Engram were performing in-memory filtering of all memories, which scales poorly. Adding database indexes on project_id and moving filtering to SQL significantly improves performance.
**Action:** Always prefer SQL-level filtering for project-scoped data and ensure foreign keys have indexes.
