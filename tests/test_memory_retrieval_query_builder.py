"""Tests for task retrieval query builder."""

from dataclasses import asdict

import engram.cli as cli_root
from engram.memory_retrieval.query_builder import (
    RetrievalQueryBuilderOptions,
    RetrievalQueryMetadata,
    build_task_retrieval_query,
)
from engram.models.phase import Phase
from engram.models.task import Task


def test_query_builder_handles_minimal_task():
    task = Task(
        id="task001",
        project_id="proj001",
        title="Ship retrieval API",
    )

    query = build_task_retrieval_query(task)

    assert query.query_text == "task.title: Ship retrieval API"
    assert query.fragments == ("task.title: Ship retrieval API",)
    assert query.metadata.task_id == "task001"
    assert query.metadata.project_id == "proj001"
    assert query.metadata.included_fields == ("task.title",)
    assert "task.description" in query.metadata.omitted_fields
    assert "task.acceptance" in query.metadata.omitted_fields
    assert "task.tags" in query.metadata.omitted_fields
    assert "task.evidence" in query.metadata.omitted_fields
    assert query.metadata.max_query_chars == 1200
    assert query.metadata.field_char_limit == 220
    assert query.metadata.uncapped_query_char_count == len(query.query_text)


def test_query_builder_is_deterministic_with_phase_and_context():
    task = Task(
        id="task002",
        project_id="proj001",
        title="Implement retrieval query builder",
        description="Build deterministic query text.",
        acceptance="Includes task and phase context for retrieval.",
        tags=["memory", "retrieval", "memory"],
    )
    phase = Phase(
        id="phase002",
        project_id="proj001",
        title="Memory Retrieval Phase 4",
        description="Create a backend-agnostic query builder.",
        acceptance="Startup and related-to-task share the same builder.",
    )
    context = {
        "repo": "engram",
        "area": "startup retrieval",
    }
    options = RetrievalQueryBuilderOptions(field_char_limit=120)

    first = build_task_retrieval_query(task, active_phase=phase, context=context, options=options)
    second = build_task_retrieval_query(task, active_phase=phase, context=context, options=options)

    assert first == second
    assert first.metadata.phase_id == "phase002"
    assert "task.tags: memory, retrieval" in first.query_text
    assert "phase.title: Memory Retrieval Phase 4" in first.query_text
    assert "context.area: startup retrieval" in first.query_text
    assert "context.repo: engram" in first.query_text
    assert "phase.evidence" in first.metadata.omitted_fields


def test_query_builder_resolves_phase_context_from_task_phase_id(tmp_db, project):
    phase = Phase.create(
        project_id=project.id,
        title="Phase Linked",
        description="Phase resolved by task phase_id.",
        acceptance="Phase acceptance details are included.",
    )
    task = Task(
        id="task004",
        project_id=project.id,
        title="Query from linked phase",
        phase_id=phase.id,
    )

    query = build_task_retrieval_query(task)

    assert query.metadata.phase_id == phase.id
    assert query.metadata.phase_title == "Phase Linked"
    assert "phase.title: Phase Linked" in query.query_text
    assert "phase.description: Phase resolved by task phase_id." in query.query_text
    assert "phase.acceptance: Phase acceptance details are included." in query.query_text


def test_query_builder_falls_back_to_legacy_phase_title_when_phase_id_not_resolved():
    task = Task(
        id="task005",
        project_id="proj001",
        title="Legacy phase fallback",
        phase="Legacy Retrieval Phase",
        phase_id="missing-phase-id",
    )

    query = build_task_retrieval_query(task)

    assert query.metadata.phase_id == "missing-phase-id"
    assert query.metadata.phase_title == "Legacy Retrieval Phase"
    assert "phase.title: Legacy Retrieval Phase" in query.query_text
    assert "phase.description" in query.metadata.omitted_fields
    assert "phase.acceptance" in query.metadata.omitted_fields


def test_query_builder_does_not_perform_database_search(monkeypatch):
    task = Task(
        id="task003",
        project_id="proj001",
        title="No DB query required",
        description="Only build retrieval text.",
    )
    search_call_count = {"count": 0}

    def _forbidden_memory_search(*args, **kwargs):
        search_call_count["count"] += 1
        raise AssertionError("Memory.search should not be used by query builder.")

    monkeypatch.setattr("engram.models.memory.Memory.search", _forbidden_memory_search)

    query = build_task_retrieval_query(task)

    assert query.query_text.startswith("task.title: No DB query required")
    assert search_call_count["count"] == 0


def test_query_builder_compacts_long_task_and_phase_fields():
    task = Task(
        id="task006",
        project_id="proj001",
        title="Title " + ("x" * 120),
        description="Description " + ("y" * 140),
        acceptance="Acceptance " + ("z" * 140),
        evidence="Evidence should be omitted " + ("e" * 140),
    )
    phase = Phase(
        id="phase006",
        project_id="proj001",
        title="Phase " + ("p" * 80),
        description="Phase description " + ("d" * 140),
        acceptance="Phase acceptance " + ("a" * 140),
        evidence="Phase evidence omitted " + ("v" * 140),
    )
    options = RetrievalQueryBuilderOptions(field_char_limit=40, max_query_chars=1200)

    query = build_task_retrieval_query(task, active_phase=phase, options=options)

    assert query.metadata.query_was_capped is False
    assert "task.evidence" in query.metadata.omitted_fields
    assert "phase.evidence" in query.metadata.omitted_fields
    assert "Evidence should be omitted" not in query.query_text
    assert "Phase evidence omitted" not in query.query_text
    assert "task.title" in query.metadata.truncated_fields
    assert "task.description" in query.metadata.truncated_fields
    assert "task.acceptance" in query.metadata.truncated_fields
    assert "phase.title" in query.metadata.truncated_fields
    assert "phase.description" in query.metadata.truncated_fields
    assert "phase.acceptance" in query.metadata.truncated_fields
    assert "task.title: " + ("x" * 40) not in query.query_text
    assert "phase.description: " + ("d" * 40) not in query.query_text


def test_query_builder_hard_budget_boundary_is_deterministic():
    task = Task(
        id="task007",
        project_id="proj001",
        title="Very long retrieval title " + ("t" * 160),
        description="Very long retrieval description " + ("d" * 200),
        acceptance="Very long retrieval acceptance " + ("a" * 200),
        tags=["tag-one", "tag-two"],
    )
    options = RetrievalQueryBuilderOptions(field_char_limit=120, max_query_chars=90)

    first = build_task_retrieval_query(task, options=options)
    second = build_task_retrieval_query(task, options=options)

    assert first == second
    assert first.metadata.query_was_capped is True
    assert first.metadata.max_query_chars == 90
    assert first.metadata.query_char_count == 90
    assert len(first.query_text) == 90
    assert first.metadata.uncapped_query_char_count > first.metadata.query_char_count


def test_query_builder_debug_metadata_contract_is_stable():
    task = Task(
        id="task008",
        project_id="proj001",
        title="Build query metadata contract",
        description="Ensure metadata output is deterministic for debug snapshots.",
        acceptance="Expose text, included fields, omitted fields, and budgets.",
        tags=["retrieval", "phase-4"],
        evidence="Task evidence is intentionally excluded from query text.",
    )
    phase = Phase(
        id="phase008",
        project_id="proj001",
        title="Phase 4 Query Builder",
        description="Prepare handoff metadata for retrieval debug commands.",
        acceptance="Metadata contract is explicit and stable.",
        evidence="Phase evidence must also be excluded.",
    )
    context = {
        "actor": "engram start",
        "surface": "debug retrieval",
    }
    options = RetrievalQueryBuilderOptions(max_query_chars=1200, field_char_limit=48)

    query = build_task_retrieval_query(task, active_phase=phase, context=context, options=options)
    metadata_dict = asdict(query.metadata)

    assert list(metadata_dict.keys()) == list(RetrievalQueryMetadata.__dataclass_fields__.keys())
    assert query.metadata.included_fields == (
        "task.title",
        "task.description",
        "task.acceptance",
        "task.tags",
        "phase.title",
        "phase.description",
        "phase.acceptance",
        "context.actor",
        "context.surface",
    )
    assert query.metadata.omitted_fields == ("task.evidence", "phase.evidence")
    assert query.metadata.truncated_fields == (
        "task.description",
        "task.acceptance",
        "phase.description",
    )
    assert query.metadata.max_query_chars == 1200
    assert query.metadata.field_char_limit == 48
    assert query.metadata.uncapped_query_char_count >= query.metadata.query_char_count
    assert query.metadata.query_char_count == len(query.query_text)
    assert "task.title: Build query metadata contract" in query.query_text
    assert "context.actor: engram start" in query.query_text
    assert "context.surface: debug retrieval" in query.query_text


def test_query_builder_does_not_require_current_project_resolution(monkeypatch):
    task = Task(
        id="task009",
        project_id="proj999",
        title="Callable from non-CLI code",
        description="Builder should only need the provided task/phase inputs.",
    )
    phase = Phase(
        id="phase009",
        project_id="proj999",
        title="Independent query builder",
    )

    def _forbidden_current_project(*args, **kwargs):
        raise AssertionError("CLI current-project resolution should not be used by query builder.")

    monkeypatch.setattr(cli_root, "get_current_project", _forbidden_current_project)

    query = build_task_retrieval_query(task, active_phase=phase)

    assert query.metadata.project_id == "proj999"
    assert query.metadata.phase_id == "phase009"
