"""Regression tests for packaged console entrypoints and install metadata."""

from importlib.metadata import distribution, entry_points

from click.testing import CliRunner

from engram.cli import cli, main
from engram.models.project import Project


def test_console_entrypoint_resolves_to_package_main():
    """The installed console script must keep loading engram.cli:main."""
    scripts = entry_points(group="console_scripts")
    engram_entrypoint = next(ep for ep in scripts if ep.name == "engram")

    assert engram_entrypoint.value == "engram.cli:main"
    assert engram_entrypoint.load() is main


def test_mcp_console_entrypoint_declared():
    """The MCP adapter entrypoint should be declared in package metadata."""
    scripts = entry_points(group="console_scripts")
    mcp_entrypoint = next(ep for ep in scripts if ep.name == "engram-mcp")

    assert mcp_entrypoint.value == "engram.mcp.server:main"
    assert callable(mcp_entrypoint.load())


def test_mcp_optional_extra_declared():
    """The package should publish a bounded MCP optional dependency extra."""
    requires = distribution("engram").requires or []

    assert any(
        requirement.startswith("mcp")
        and ">=1.0" in requirement
        and "<2" in requirement
        and 'extra == "mcp"' in requirement
        for requirement in requires
    )


def test_console_entrypoint_command_surface_loads():
    """Loading the Click root command through the package exposes essential commands."""
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output

    exposed_commands = list(cli.commands.keys())
    assert sorted(exposed_commands) == sorted(["init", "guide", "db"])


def test_guide_command_runs_successfully():
    """The guide command should render and exit successfully."""
    result = CliRunner().invoke(cli, ["guide"])
    assert result.exit_code == 0, result.output
    assert "Engram User Manual" in result.output


def test_guide_command_with_sections():
    """The guide command with specific sections should render and exit successfully."""
    for section in ["concepts", "commands", "workflow", "troubleshooting"]:
        result = CliRunner().invoke(cli, ["guide", section])
        assert result.exit_code == 0, result.output
        assert "Engram Guide" in result.output


def test_db_command_runs_successfully(tmp_db):
    """The db command should execute health checks on the database."""
    result = CliRunner().invoke(cli, ["db"])
    assert result.exit_code == 0, result.output
    assert "Database Path:" in result.output
    assert "Database Exists: Yes" in result.output
    assert "Database Connection & Integrity: Healthy" in result.output


def test_init_command_reports_already_bound_project(project, monkeypatch, tmp_path):
    """Init should not create or rebind when the current repo is already registered."""
    monkeypatch.chdir(tmp_path)
    project.add_repo_path(str(tmp_path))

    result = CliRunner().invoke(cli, ["init", "--name", "Ignored", "--id", "ignored"])

    assert result.exit_code == 0, result.output
    assert "already bound to project" in result.output
    assert project.id in result.output


def test_init_command_binds_existing_project_id(project, monkeypatch, tmp_path):
    """Init should bind the current repo when the requested project id already exists."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["init", "--name", "Renamed", "--id", project.id])

    assert result.exit_code == 0, result.output
    assert f"Project '{project.id}' already exists" in result.output
    assert str(tmp_path) in Project.get(project.id).repo_paths


def test_init_command_creates_slugged_project_when_id_is_omitted(tmp_db, monkeypatch, tmp_path):
    """Init should slugify the prompted project name when --id is not supplied."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli,
        ["init", "--name", "My New Project", "--summary", "Created from CLI"],
    )

    assert result.exit_code == 0, result.output
    assert "Initialized project 'my-new-project'" in result.output
    created = Project.get("my-new-project")
    assert created is not None
    assert created.name == "My New Project"
    assert created.summary == "Created from CLI"
    assert str(tmp_path) in created.repo_paths


def test_guide_command_reports_manual_read_errors(monkeypatch):
    """Guide should surface packaged manual loading failures without crashing."""

    class BrokenPackageFiles:
        def __truediv__(self, _name):
            return self

        def read_text(self, encoding="utf-8"):
            raise OSError("manual missing")

    monkeypatch.setattr("engram.cli.utils_cmds.resources.files", lambda _package: BrokenPackageFiles())

    result = CliRunner().invoke(cli, ["guide"])

    assert result.exit_code == 0, result.output
    assert "Error reading manual" in result.output
    assert "manual missing" in result.output


def test_db_command_reports_size_and_connection_errors(monkeypatch, tmp_path):
    """DB command should handle stat and connection failures independently."""

    class BrokenDbPath:
        def exists(self):
            return True

        def stat(self):
            raise OSError("stat denied")

        def __str__(self):
            return str(tmp_path / "broken.db")

    def raise_connection_error():
        raise RuntimeError("cannot open db")

    monkeypatch.setattr("engram.db.DEFAULT_DB_PATH", BrokenDbPath())
    monkeypatch.setattr("engram.db.get_db_connection", raise_connection_error)

    result = CliRunner().invoke(cli, ["db"])

    assert result.exit_code == 0, result.output
    assert "Database Exists: Yes" in result.output
    assert "Error reading size" in result.output
    assert "Database Connection Error" in result.output
    assert "cannot open db" in result.output
