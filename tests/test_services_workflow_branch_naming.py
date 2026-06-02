"""Tests for workflow branch naming based on explicit plan and phase keys."""

from __future__ import annotations

from typing import Any

import pytest

from engram.models.phase import Phase
from engram.models.project import Project
from engram.models.task import Task
from engram.services.errors import EngramServiceError
from engram.services.workflow_helpers import get_target_branch


def test_get_target_branch_uses_explicit_keys(tmp_db: Any) -> None:
    """Verify branch names are derived from stored plan and phase keys."""
    project = Project.create(
        id="proj-branch-1",
        name="Project Branch 1",
        summary="Branch naming test",
        repo_paths=["/tmp/proj-branch-1"],
    )
    phase = Phase.create(
        project_id=project.id,
        id="ph-branch-1",
        title="Branch Phase",
        status="active",
    )
    task = Task.create(
        project_id=project.id,
        id="task-branch-1",
        title="Branch task",
        phase_id=phase.id,
        phase="Branch Phase",
        status="open",
    )

    assert get_target_branch(task, project, phase=phase) == "feat/proj-branch-1-ph-branch-1"


@pytest.mark.parametrize(
    ("plan_key", "phase_key", "missing_field"),
    [
        ("", "ph-branch-1", "plan_key"),
        ("proj-branch-1", "", "phase_key"),
    ],
)
def test_get_target_branch_blocks_when_required_keys_are_missing(
    tmp_db: Any, plan_key: str, phase_key: str, missing_field: str
) -> None:
    """Verify missing explicit keys produce actionable errors."""
    project = Project.create(
        id="proj-branch-1",
        name="Project Branch 1",
        summary="Branch naming test",
        repo_paths=["/tmp/proj-branch-1"],
    )
    project.plan_key = plan_key
    phase = Phase.create(
        project_id=project.id,
        id="ph-branch-1",
        title="Branch Phase",
        status="active",
    )
    phase.key = phase_key
    task = Task.create(
        project_id=project.id,
        id="task-branch-1",
        title="Branch task",
        phase_id=phase.id,
        phase="Branch Phase",
        status="open",
    )

    with pytest.raises(EngramServiceError) as exc_info:
        get_target_branch(task, project, phase=phase)

    assert exc_info.value.code == "WORKFLOW_BRANCH_KEYS_MISSING"
    assert missing_field in exc_info.value.message
    assert missing_field in exc_info.value.details["missing_fields"]
    assert exc_info.value.fix is not None


def test_get_target_branch_returns_misc_for_unphased_task(tmp_db: Any) -> None:
    """Verify unphased tasks keep the explicit misc fallback."""
    project = Project.create(
        id="proj-branch-2",
        name="Project Branch 2",
        summary="Branch naming test",
        repo_paths=["/tmp/proj-branch-2"],
    )
    task = Task.create(
        project_id=project.id,
        id="task-branch-2",
        title="Unphased task",
        status="open",
    )

    assert get_target_branch(task, project) == "feat/misc"
