"""Regression tests for the packaged CLI entrypoint."""

from importlib.metadata import entry_points

from click.testing import CliRunner

from engram.cli import cli, main


def test_console_entrypoint_resolves_to_package_main():
    """The installed console script must keep loading engram.cli:main."""
    scripts = entry_points(group="console_scripts")
    engram_entrypoint = next(ep for ep in scripts if ep.name == "engram")

    assert engram_entrypoint.value == "engram.cli:main"
    assert engram_entrypoint.load() is main


def test_console_entrypoint_command_surface_loads():
    """Loading the Click root command through the package exposes migrated commands."""
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0, result.output
    for command in [
        "context",
        "decision",
        "export",
        "memory",
        "project",
        "session",
        "task",
    ]:
        assert command in result.output
