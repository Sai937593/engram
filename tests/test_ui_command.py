"""CLI tests for the local UI command."""

from click.testing import CliRunner

from engram.cli import cli
from engram.models.project import Project
from engram.ui import state as ui_state


def test_ui_command_writes_latest_project_state(project, tmp_path, monkeypatch):
    """Running engram ui from a registered repo selects that project."""
    repo = tmp_path / "repo"
    repo.mkdir()
    project.add_repo_path(str(repo))
    state_path = tmp_path / "ui_state.json"
    served = {}
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ui_state, "DEFAULT_UI_STATE_PATH", state_path)
    monkeypatch.setattr("engram.cli.ui_cmds._is_port_open", lambda host, port: False)
    monkeypatch.setattr("engram.cli.ui_cmds._import_uvicorn", lambda: None)
    monkeypatch.setattr(
        "engram.cli.ui_cmds._serve_app",
        lambda app, host, port: served.update({"host": host, "port": port}),
    )
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    result = CliRunner().invoke(cli, ["ui"])

    assert result.exit_code == 0, result.output
    assert served == {"host": "127.0.0.1", "port": 8765}
    assert ui_state.read_target(state_path).project_id == project.id


def test_ui_command_updates_running_engram_ui(project, tmp_path, monkeypatch):
    """A compatible running UI receives the latest project through state."""
    repo = tmp_path / "repo"
    repo.mkdir()
    project.add_repo_path(str(repo))
    state_path = tmp_path / "ui_state.json"
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ui_state, "DEFAULT_UI_STATE_PATH", state_path)
    monkeypatch.setattr("engram.cli.ui_cmds._is_port_open", lambda host, port: True)
    monkeypatch.setattr(
        "engram.cli.ui_cmds._read_running_engram_ui",
        lambda url: {"app": "engram-ui", "project_id": "old"},
    )
    monkeypatch.setattr(
        "engram.cli.ui_cmds._serve_app",
        lambda app, host, port: (_ for _ in ()).throw(AssertionError("server started")),
    )
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    result = CliRunner().invoke(cli, ["ui"])

    assert result.exit_code == 0, result.output
    assert "Engram UI updated" in result.output
    assert ui_state.read_target(state_path).project_id == project.id


def test_ui_command_fails_on_non_engram_busy_port(project, tmp_path, monkeypatch):
    """A busy non-Engram port fails without changing UI state."""
    repo = tmp_path / "repo"
    repo.mkdir()
    project.add_repo_path(str(repo))
    state_path = tmp_path / "ui_state.json"
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ui_state, "DEFAULT_UI_STATE_PATH", state_path)
    monkeypatch.setattr("engram.cli.ui_cmds._is_port_open", lambda host, port: True)
    monkeypatch.setattr("engram.cli.ui_cmds._read_running_engram_ui", lambda url: None)
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    result = CliRunner().invoke(cli, ["ui"])

    assert result.exit_code != 0
    assert "not a compatible Engram UI server" in result.output
    assert not state_path.exists()


def test_ui_command_unregistered_cwd_errors(tmp_db, tmp_path, monkeypatch):
    """Launching from an unregistered directory does not fall back to Engram."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ui_state, "DEFAULT_UI_STATE_PATH", tmp_path / "ui_state.json")
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    result = CliRunner().invoke(cli, ["ui"])

    assert result.exit_code != 0
    assert "engram init" in result.output


def test_ui_command_duplicate_repo_binding_errors(tmp_db, tmp_path, monkeypatch):
    """Duplicate project bindings fail clearly from the CLI."""
    repo = tmp_path / "repo"
    repo.mkdir()
    Project.create("proj-a", "Project A", repo_paths=[str(repo)])
    Project.create("proj-b", "Project B", repo_paths=[str(repo)])
    monkeypatch.chdir(repo)
    monkeypatch.setattr(ui_state, "DEFAULT_UI_STATE_PATH", tmp_path / "ui_state.json")
    monkeypatch.setattr(ui_state, "_git_root", lambda path: None)

    result = CliRunner().invoke(cli, ["ui"])

    assert result.exit_code != 0
    assert "matches multiple Engram projects" in result.output
