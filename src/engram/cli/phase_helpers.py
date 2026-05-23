"""Shared helpers for CLI phase reference resolution."""

import click

from engram.models.phase import Phase


def normalize_phase_title(title: str | None) -> str:
    """Return a case-insensitive, whitespace-normalized title key."""
    if title is None:
        return ""
    return " ".join(title.split()).casefold()


def resolve_phase_in_project(value: str, project_id: str) -> Phase:
    """Resolve a phase by exact ID first, then unique normalized title."""
    candidate = value.strip()
    if not candidate:
        raise click.ClickException("Phase reference cannot be empty.")

    phase = Phase.get(candidate)
    if phase and phase.project_id == project_id:
        return phase

    normalized_candidate = normalize_phase_title(candidate)
    matching_phases = [
        project_phase
        for project_phase in Phase.list_by_project(project_id)
        if normalize_phase_title(project_phase.title) == normalized_candidate
    ]

    if len(matching_phases) == 1:
        return matching_phases[0]

    if len(matching_phases) > 1:
        matches = ", ".join(f"{match.id} ({match.title})" for match in matching_phases)
        raise click.ClickException(
            f"Ambiguous phase '{value}'. Multiple phases match this title: {matches}"
        )

    raise click.ClickException(f"Phase '{value}' not found in this project.")
