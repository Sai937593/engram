"""Plan services implementing core plan lifecycle operations."""

from __future__ import annotations

from pathlib import Path

from engram.models.plan import Plan
from engram.models.project import Project
from engram.services.errors import EngramServiceError, JsonValue, ValidationError
from engram.services.serializers import plan_to_dict


def resolve_plan_ref(project_id: str, plan_ref: str, db_path: str | Path | None = None) -> Plan:
    """Resolve a plan by its ID or project-scoped key."""
    candidate = plan_ref.strip()
    if not candidate:
        raise ValidationError(
            code="INVALID_PLAN_REFERENCE",
            message="Plan reference cannot be empty.",
            details={"plan_ref": plan_ref},
        )
    plan = Plan.get(candidate, db_path=db_path)
    if plan and plan.project_id == project_id:
        return plan
    plan = Plan.get_by_key(project_id, candidate, db_path=db_path)
    if plan:
        return plan

    raise ValidationError(
        code="PLAN_NOT_FOUND",
        message=f"Plan '{candidate}' not found in this project.",
        details={"project_id": project_id, "plan_ref": candidate},
    )


def get_current_plan(project_id: str, db_path: str | Path | None = None) -> dict[str, JsonValue]:
    """Return the active plan for the current project."""
    project = Project.get(project_id, db_path=db_path)
    if not project:
        raise ValidationError(
            code="PROJECT_NOT_FOUND",
            message=f"Project '{project_id}' not found.",
            details={"project_id": project_id},
        )
    active_plan = project.get_active_plan(db_path=db_path)
    if not active_plan:
        raise EngramServiceError(
            code="ACTIVE_PLAN_MISSING",
            message=f"No active plan found for project '{project_id}'.",
            details={"project_id": project_id},
        )
    return plan_to_dict(active_plan)


def _deactivate_others(project_id: str, active_id: str, db_path: str | Path | None = None) -> None:
    from engram.db import get_db_connection

    conn = get_db_connection(db_path) if db_path is not None else get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id FROM plans WHERE project_id = ? AND status = 'active' AND id != ?",
            (project_id, active_id),
        ).fetchall()
        for r in rows:
            p = Plan.get(r["id"], db_path=db_path)
            if p:
                p.update(status="draft", db_path=db_path)
    finally:
        conn.close()


def create_plan(
    project_id: str,
    title: str,
    slug: str | None = None,
    status: str = "draft",
    source_doc_path: str | None = None,
    key: str | None = None,
    activate: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, JsonValue]:
    """Create a new plan record and optionally activate it."""
    if status not in Plan.VALID_STATUSES:
        raise ValidationError(
            code="INVALID_PLAN_STATUS",
            message=f"Plan status '{status}' is invalid.",
            details={"status": status, "allowed_statuses": sorted(Plan.VALID_STATUSES)},
        )
    try:
        plan = Plan.create(
            project_id=project_id,
            title=title,
            slug=slug,
            status=status,
            source_doc_path=source_doc_path,
            key=key,
            db_path=db_path,
        )
    except ValueError as exc:
        raise ValidationError(
            code="DUPLICATE_PLAN_KEY",
            message=str(exc),
            details={"project_id": project_id, "key": key},
        ) from exc

    if activate:
        activate_plan(project_id, plan.id, db_path=db_path)
        plan = Plan.get(plan.id, db_path=db_path) or plan

    return plan_to_dict(plan)


def activate_plan(
    project_id: str, plan_ref: str, db_path: str | Path | None = None
) -> dict[str, JsonValue]:
    """Enforce exactly one active plan for the project and link it."""
    project = Project.get(project_id, db_path=db_path)
    if not project:
        raise ValidationError(
            code="PROJECT_NOT_FOUND",
            message=f"Project '{project_id}' not found.",
            details={"project_id": project_id},
        )
    plan = resolve_plan_ref(project_id, plan_ref, db_path=db_path)
    _deactivate_others(project_id, plan.id, db_path=db_path)
    plan.update(status="active", db_path=db_path)
    project.update(active_plan_id=plan.id, db_path=db_path)
    return plan_to_dict(plan)


def update_plan(
    project_id: str,
    plan_ref: str,
    title: str | None = None,
    slug: str | None = None,
    status: str | None = None,
    source_doc_path: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, JsonValue]:
    """Update mutable plan fields."""
    project = Project.get(project_id, db_path=db_path)
    if not project:
        raise ValidationError(
            code="PROJECT_NOT_FOUND",
            message=f"Project '{project_id}' not found.",
            details={"project_id": project_id},
        )
    plan = resolve_plan_ref(project_id, plan_ref, db_path=db_path)

    if status == "active":
        _deactivate_others(project_id, plan.id, db_path=db_path)
        project.update(active_plan_id=plan.id, db_path=db_path)

    plan.update(
        title=title,
        slug=slug,
        status=status,
        source_doc_path=source_doc_path,
        db_path=db_path,
    )

    if status is not None and status != "active" and plan.id == project.active_plan_id:
        project.update(active_plan_id=None, db_path=db_path)

    return plan_to_dict(plan)


def list_plans(
    project_id: str, status: str | None = None, db_path: str | Path | None = None
) -> list[dict[str, JsonValue]]:
    """List plans for a project, optionally filtering by status."""
    plans = Plan.list_by_project(project_id, db_path=db_path)
    if status is not None:
        normalized_status = status.strip().casefold()
        if normalized_status not in Plan.VALID_STATUSES and normalized_status != "all":
            raise ValidationError(
                code="INVALID_PLAN_STATUS",
                message=f"Plan status filter '{status}' is invalid.",
                details={"status": status, "allowed_statuses": sorted(Plan.VALID_STATUSES)},
            )
        if normalized_status != "all":
            plans = [p for p in plans if p.status == normalized_status]
    return [plan_to_dict(p) for p in plans]


def get_plan(
    project_id: str, plan_ref: str, db_path: str | Path | None = None
) -> dict[str, JsonValue]:
    """Get full details of a plan by ID or key."""
    plan = resolve_plan_ref(project_id, plan_ref, db_path=db_path)
    return plan_to_dict(plan)
