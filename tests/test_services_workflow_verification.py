import pytest

from engram.services.errors import EngramServiceError
from engram.services.workflow_verification_service import (
    get_latest_workflow_verification,
    record_workflow_verification,
)


def test_record_and_get_latest_workflow_verification_by_task(project, task):
    first = record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=False,
        summary="lint failed",
        details="ruff reported E501",
        verified_at="2026-05-30 10:00:00",
    )
    second = record_workflow_verification(
        project_id=project.id,
        task_id=task.id,
        passed=True,
        summary="all checks passed",
        verified_at="2026-05-31 10:00:00",
    )

    latest = get_latest_workflow_verification(project_id=project.id, task_id=task.id)
    assert first["status"] == "failed"
    assert second["status"] == "passed"
    assert latest is not None
    assert latest["id"] == second["id"]
    assert latest["summary"] == "all checks passed"


def test_get_latest_workflow_verification_by_workflow_run(project):
    record_workflow_verification(
        project_id=project.id,
        workflow_run_ref="run-001",
        passed=True,
        summary="verify green",
    )
    latest = get_latest_workflow_verification(project_id=project.id, workflow_run_ref="run-001")
    assert latest is not None
    assert latest["workflow_run_ref"] == "run-001"
    assert latest["status"] == "passed"


def test_record_workflow_verification_requires_task_or_run(project):
    with pytest.raises(EngramServiceError) as exc:
        record_workflow_verification(
            project_id=project.id,
            passed=True,
            summary="missing target",
        )
    assert exc.value.code == "VALIDATION_ERROR"
