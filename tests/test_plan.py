"""Tests for the plan model."""

from __future__ import annotations

import pytest

from engram.models.plan import Plan
from engram.models.project import Project


def test_create_plan_persists_and_queries_by_id(tmp_db):
    project = Project.create(
        id="proj-plan-1",
        name="Plan Project",
        summary="Project with plans",
        repo_paths=["/tmp/plan-project"],
        db_path=tmp_db,
    )

    plan = Plan.create(
        project_id=project.id,
        title="First implementation plan",
        slug="first-implementation-plan",
        status="active",
        source_doc_path="docs/plans/p0004/adr.md",
        key="p0004",
        db_path=tmp_db,
    )

    assert plan.id
    assert plan.project_id == project.id
    assert plan.key == "p0004"
    assert plan.title == "First implementation plan"
    assert plan.slug == "first-implementation-plan"
    assert plan.status == "active"
    assert plan.source_doc_path == "docs/plans/p0004/adr.md"

    fetched = Plan.get(plan.id, db_path=tmp_db)
    assert fetched is not None
    assert fetched.id == plan.id
    assert fetched.project_id == project.id
    assert fetched.key == "p0004"
    assert fetched.title == "First implementation plan"

    by_key = Plan.get_by_key(project.id, "p0004", db_path=tmp_db)
    assert by_key is not None
    assert by_key.id == plan.id

    plans = Plan.list_by_project(project.id, db_path=tmp_db)
    assert [item.id for item in plans] == [plan.id]


@pytest.mark.parametrize(
    ("field_name", "kwargs", "message"),
    [
        ("project_id", {"project_id": " ", "title": "Plan title"}, "project_id is required"),
        ("title", {"project_id": "proj-req", "title": " "}, "title is required"),
    ],
)
def test_create_plan_rejects_missing_required_fields(tmp_db, field_name, kwargs, message):
    project = Project.create(
        id="proj-req",
        name="Required Fields",
        repo_paths=["/tmp/required-fields"],
        db_path=tmp_db,
    )
    kwargs.setdefault("project_id", project.id)
    with pytest.raises(ValueError, match=message):
        Plan.create(db_path=tmp_db, **kwargs)


def test_create_plan_rejects_invalid_status(tmp_db):
    project = Project.create(
        id="proj-status",
        name="Status Project",
        repo_paths=["/tmp/status-project"],
        db_path=tmp_db,
    )

    with pytest.raises(ValueError, match="Invalid plan status"):
        Plan.create(project_id=project.id, title="Plan", status="broken", db_path=tmp_db)


def test_plan_keys_are_unique_within_project_scope(tmp_db):
    project_one = Project.create(
        id="proj-unique-1",
        name="Unique One",
        repo_paths=["/tmp/unique-one"],
        db_path=tmp_db,
    )
    project_two = Project.create(
        id="proj-unique-2",
        name="Unique Two",
        repo_paths=["/tmp/unique-two"],
        db_path=tmp_db,
    )

    first = Plan.create(
        project_id=project_one.id,
        title="Primary plan",
        key="p0004",
        db_path=tmp_db,
    )
    second = Plan.create(
        project_id=project_two.id,
        title="Secondary plan",
        key="p0004",
        db_path=tmp_db,
    )

    assert first.key == "p0004"
    assert second.key == "p0004"
    assert Plan.get_by_key(project_one.id, "p0004", db_path=tmp_db).id == first.id
    assert Plan.get_by_key(project_two.id, "p0004", db_path=tmp_db).id == second.id

    with pytest.raises(ValueError, match="already exists in this project"):
        Plan.create(
            project_id=project_one.id,
            title="Duplicate key plan",
            key="p0004",
            db_path=tmp_db,
        )
