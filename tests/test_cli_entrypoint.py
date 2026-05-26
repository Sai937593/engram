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
    """Loading the Click root command through the package exposes migrated commands."""
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0, result.output
    for command in [
        "context",
        "decision",
        "export",
        "guardrail",
        "memory",
        "phase",
        "project",
        "task",
    ]:
        assert command in result.output


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


def test_phase_group_help_loads():
    """The phase command group should load and render help text."""
    result = CliRunner().invoke(cli, ["phase", "--help"])

    assert result.exit_code == 0, result.output
    assert "Manage phases." in result.output
