from engram.db import get_db_connection
from engram.memory_retrieval.fts_query import normalize_fts_query_text
from engram.models.memory.model import Memory


def list_by_project(project_id: str) -> list[Memory]:
    """Return all memories for a project ordered by creation date."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE project_id = ? ORDER BY created_at ASC", (project_id,)
    ).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]


def list_by_type(project_id: str, memory_type: str) -> list[Memory]:
    """Return memories of a specific type for a project, ordered by creation date."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE project_id = ? AND type = ? ORDER BY created_at ASC",
        (project_id, memory_type),
    ).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]


def list_project_guardrail_candidates(project_id: str) -> list[Memory]:
    """Return project-scope L0/L1 memories ordered for deterministic guardrail retrieval."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM memories
        WHERE project_id = ? AND scope = 'project' AND level IN ('L0', 'L1')
        ORDER BY
            CASE level WHEN 'L0' THEN 0 WHEN 'L1' THEN 1 ELSE 2 END,
            id ASC
        """,
        (project_id,),
    ).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]


def list_task_scope_for_project(project_id: str) -> list[Memory]:
    """Return task-scope memories for a project in deterministic order."""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT *
        FROM memories
        WHERE project_id = ? AND scope = 'task'
        ORDER BY created_at ASC, id ASC
        """,
        (project_id,),
    ).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]


def list_always_include(project_id: str) -> list[Memory]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE project_id = ? AND always_include = 1", (project_id,)
    ).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]


def get(id: str) -> Memory | None:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM memories WHERE id = ?", (id,)).fetchone()
    conn.close()
    if row:
        return Memory.from_row(row)
    return None


def search(
    query: str | None,
    type_filter: str | None = None,
    tag_filters: list[str] | None = None,
    project_id: str | None = None,
) -> list[Memory]:
    """Search memories using a normalized FTS-safe query string."""
    conn = get_db_connection()

    safe_query = normalize_fts_query_text(query)
    sql = """
        SELECT m.* FROM memories m
        JOIN memories_fts f ON m.rowid = f.rowid
        WHERE memories_fts MATCH ?
    """
    params = [safe_query]

    if project_id:
        sql += " AND m.project_id = ?"
        params.append(project_id)

    if type_filter:
        sql += " AND m.type = ?"
        params.append(type_filter)

    if tag_filters:
        for tag in tag_filters:
            # Simple LIKE search for tags in MVP
            sql += " AND m.tags LIKE ?"
            params.append(f"%{tag}%")

    sql += " ORDER BY rank"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [Memory.from_row(row) for row in rows]
