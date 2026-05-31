"""Regression tests for packaged console entrypoints and install metadata."""

from importlib.metadata import distribution, entry_points

from click.testing import CliRunner

from engram.cli import cli, main


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


def test_console_help_does_not_eagerly_initialize_db(monkeypatch):
    """CLI startup/help should not initialize a database."""
    called = {"value": False}

    def fail_init(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("init_db should not run during CLI help bootstrap")

    monkeypatch.setattr("engram.db.init_db", fail_init)

    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert called["value"] is False


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


def test_db_command_runs_successfully(monkeypatch, tmp_path):
    """The db command should execute health checks inside a git repo."""
    repo_root = tmp_path
    (repo_root / ".git").mkdir(exist_ok=True)
    monkeypatch.setattr("os.getcwd", lambda: str(repo_root))
    result = CliRunner().invoke(cli, ["db"])
    assert result.exit_code == 0, result.output
    assert "Database Path:" in result.output
    assert ".engram" in result.output
    assert "memory.db" in result.output
    assert "Database Exists: Yes" in result.output
    assert "Database Connection & Integrity: Healthy" in result.output
    assert (repo_root / ".engram" / "memory.db").exists()


def test_db_command_outside_repo_degrades_cleanly(monkeypatch, tmp_path):
    """The db command should report unresolved workspace outside a git repo."""
    monkeypatch.setattr("os.getcwd", lambda: str(tmp_path))
    result = CliRunner().invoke(cli, ["db"])
    assert result.exit_code == 0, result.output
    assert "Workspace: Not in a git repository" in result.output
    assert "Could not resolve repository root from the current path." in result.output
