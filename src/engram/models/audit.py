from engram.db import get_db_connection


class AuditLog:
    @staticmethod
    def log(
        target_table, target_id, operation, field=None, old_value=None, new_value=None, conn=None
    ):
        owns_connection = conn is None
        active_conn = conn if conn is not None else get_db_connection()
        active_conn.execute(
            """
            INSERT INTO audit_log (target_table, target_id, operation, field, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (target_table, target_id, operation, field, old_value, new_value),
        )
        if owns_connection:
            active_conn.commit()
            active_conn.close()

    @staticmethod
    def get_logs_for_target(target_table, target_id):
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE target_table = ? AND target_id = ? ORDER BY timestamp DESC",
            (target_table, target_id),
        ).fetchall()
        conn.close()
        return rows
