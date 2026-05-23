"""Tests for CLI phase resolution helpers."""

import click
import pytest

from engram.cli.phase_helpers import normalize_phase_title, resolve_phase_in_project
from engram.models.phase import Phase


def test_normalize_phase_title_collapses_whitespace_and_case() -> None:
    assert normalize_phase_title("  PHASE   Alpha  ") == "phase alpha"


def test_resolve_phase_in_project_prefers_exact_phase_id(project) -> None:
    by_id = Phase.create(project_id=project.id, id="phase123", title="Implementation")
    by_title = Phase.create(project_id=project.id, title="phase123")

    resolved = resolve_phase_in_project("phase123", project.id)

    assert resolved.id == by_id.id
    assert resolved.title != by_title.title


def test_resolve_phase_in_project_matches_unique_normalized_title(project) -> None:
    created = Phase.create(project_id=project.id, title="Phase   Alpha")

    resolved = resolve_phase_in_project("  phase alpha  ", project.id)

    assert resolved.id == created.id


def test_resolve_phase_in_project_errors_on_ambiguous_normalized_title(project) -> None:
    Phase.create(project_id=project.id, title="Phase Alpha")
    Phase.create(project_id=project.id, title="  phase   alpha ")

    with pytest.raises(click.ClickException, match="Ambiguous phase 'phase alpha'"):
        resolve_phase_in_project("phase alpha", project.id)


def test_resolve_phase_in_project_errors_when_missing(project) -> None:
    with pytest.raises(click.ClickException, match="Phase 'phase zeta' not found in this project"):
        resolve_phase_in_project("phase zeta", project.id)
