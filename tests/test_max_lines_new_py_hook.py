"""Tests for pre-commit max-line check on newly added Python files."""

from __future__ import annotations

import subprocess
from pathlib import Path

from engram.hooks.max_lines_new_py import (
    find_line_limit_violations,
    list_added_staged_python_files,
    run_check,
)


def test_list_added_staged_python_files_filters_to_py(monkeypatch):
    class Completed:
        stdout = "src/a.py\nsrc/b.txt\ntests/test_x.py\n"

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    files = list_added_staged_python_files()
    assert files == [Path("src/a.py"), Path("tests/test_x.py")]


def test_find_line_limit_violations_flags_only_files_over_limit(tmp_path):
    short_file = tmp_path / "short.py"
    long_file = tmp_path / "long.py"
    short_file.write_text("x\n" * 200, encoding="utf-8")
    long_file.write_text("x\n" * 201, encoding="utf-8")

    violations = find_line_limit_violations([short_file, long_file], max_lines=200, repo_root=None)

    assert violations == [(long_file, 201)]


def test_run_check_ignores_existing_modified_files_and_checks_only_new(monkeypatch, tmp_path):
    new_file = tmp_path / "new_long.py"
    existing_file = tmp_path / "existing_long.py"
    new_file.write_text("x\n" * 201, encoding="utf-8")
    existing_file.write_text("x\n" * 350, encoding="utf-8")

    monkeypatch.setattr(
        "engram.hooks.max_lines_new_py.list_added_staged_python_files",
        lambda repo_root=None: [new_file],
    )

    exit_code = run_check(max_lines=200)
    assert exit_code == 1
