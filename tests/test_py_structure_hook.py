"""Tests for the py_structure pre-commit hook."""

from __future__ import annotations

import subprocess
from pathlib import Path

from engram.hooks.py_structure import (
    check_files,
    count_lines,
    count_public_symbols,
    get_line_limit,
    get_staged_python_files,
    is_test_file,
    run_check,
)


def test_get_staged_python_files(monkeypatch):
    """Test git index query filters to staged added/modified .py files."""

    class Completed:
        stdout = "src/a.py\nsrc/b.txt\ntests/test_x.py\n"

    def fake_run(args, **kwargs):
        # Verify the exact git command arguments
        assert args == ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"]
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    files = get_staged_python_files()
    assert files == [Path("src/a.py"), Path("tests/test_x.py")]


def test_is_test_file():
    """Test detection of files under tests/ directory."""
    assert is_test_file(Path("tests/test_hook.py")) is True
    assert is_test_file(Path("src/tests/test_hook.py")) is True
    assert is_test_file(Path("src/engram/hooks/py_structure.py")) is False


def test_get_line_limit():
    """Test tiered line limits for different tiers of files."""
    # Test files are exempt
    assert get_line_limit(Path("tests/test_hook.py")) is None
    assert get_line_limit(Path("src/tests/test_hook.py")) is None

    # Top-level (3 parts) starting with src/
    assert get_line_limit(Path("src/engram/main.py")) == 150

    # Subpackage (4+ parts) starting with src/
    assert get_line_limit(Path("src/engram/hooks/py_structure.py")) == 200
    assert get_line_limit(Path("src/engram/sub/sub2/file.py")) == 200

    # Default limit
    assert get_line_limit(Path("other_folder/file.py")) == 200


def test_count_lines(tmp_path):
    """Test reading and counting lines of a file."""
    f = tmp_path / "test.py"
    f.write_text("line 1\nline 2\nline 3", encoding="utf-8")
    assert count_lines(f) == 3


def test_count_public_symbols(tmp_path):
    """Test counting top-level def and class declarations."""
    f = tmp_path / "symbols.py"
    f.write_text(
        "class A:\n"
        "    def nested(self):\n"
        "        pass\n"
        "\n"
        "def public_func():\n"
        "    pass\n"
        "\n"
        " def invalid_indent():\n"
        "    pass\n"
        "\n"
        "class B(A):\n"
        "    pass\n",
        encoding="utf-8",
    )
    # class A, def public_func, class B (exactly 3 at column 0)
    assert count_public_symbols(f) == 3


def test_check_files_no_violations(tmp_path):
    """Test check_files returns no violations for clean files."""
    f = tmp_path / "src" / "engram" / "main.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("class A:\n    pass\n", encoding="utf-8")

    violations = check_files([Path("src/engram/main.py")], repo_root=tmp_path)
    assert len(violations) == 0


def test_check_files_line_limit_violation(tmp_path):
    """Test check_files flags files exceeding tiered line limits."""
    # Top-level limit is 150. Let's create a file with 151 lines.
    top_level_file = tmp_path / "src" / "engram" / "main.py"
    top_level_file.parent.mkdir(parents=True, exist_ok=True)
    top_level_file.write_text("\n" * 151, encoding="utf-8")

    violations = check_files([Path("src/engram/main.py")], repo_root=tmp_path)
    assert len(violations) == 1
    assert "src/engram/main.py: 151 lines (limit: 150 for top-level files)" in violations[0]
    assert "→ Split into a subpackage or extract helpers to a sibling module." in violations[0]


def test_check_files_symbol_limit_violation(tmp_path):
    """Test check_files flags files exceeding public symbol limits."""
    f = tmp_path / "src" / "engram" / "main.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    # Create 9 public symbols (limit is 8)
    content = "\n".join(f"def func_{i}(): pass" for i in range(9))
    f.write_text(content, encoding="utf-8")

    violations = check_files([Path("src/engram/main.py")], repo_root=tmp_path)
    assert len(violations) == 1
    assert "src/engram/main.py: 9 public symbols (limit: 8)" in violations[0]
    assert "→ Extract related functions/classes into a sibling module." in violations[0]


def test_run_check_scenarios(monkeypatch, tmp_path):
    """Test different run_check end-to-end scenarios using exit codes."""
    # Scenario 1: No staged files -> exit 0
    monkeypatch.setattr(
        "engram.hooks.py_structure.get_staged_python_files",
        lambda repo_root=None: [],
    )
    assert run_check(repo_root=tmp_path) == 0

    # Scenario 2: Deleted/non-existent files staged -> ignored, exit 0
    monkeypatch.setattr(
        "engram.hooks.py_structure.get_staged_python_files",
        lambda repo_root=None: [Path("src/engram/deleted.py")],
    )
    assert run_check(repo_root=tmp_path) == 0

    # Scenario 3: Test file over line and symbol limits -> exempt, exit 0
    test_file = tmp_path / "tests" / "test_over.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    # 300 lines (exceeds subpackage limit 200) & 10 public symbols (exceeds 8)
    content = "\n".join(f"def test_func_{i}(): pass" for i in range(10)) + "\n" * 300
    test_file.write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        "engram.hooks.py_structure.get_staged_python_files",
        lambda repo_root=None: [Path("tests/test_over.py")],
    )
    assert run_check(repo_root=tmp_path) == 0

    # Scenario 4: Modified/added file over limit -> exit 1
    bad_file = tmp_path / "src" / "engram" / "bad.py"
    bad_file.parent.mkdir(parents=True, exist_ok=True)
    bad_file.write_text("\n" * 151, encoding="utf-8")  # top-level limit is 150

    monkeypatch.setattr(
        "engram.hooks.py_structure.get_staged_python_files",
        lambda repo_root=None: [Path("src/engram/bad.py")],
    )
    assert run_check(repo_root=tmp_path) == 1


def test_run_check_subprocess_error(monkeypatch, capsys):
    """Test run_check handles subprocess.CalledProcessError with stderr."""

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            stderr="fatal: not a git repository\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    exit_code = run_check()
    assert exit_code == 1

    captured = capsys.readouterr()
    assert (
        "py-structure: failed to inspect staged files: fatal: not a git repository" in captured.err
    )


def test_run_check_subprocess_error_no_stderr(monkeypatch, capsys):
    """Test run_check handles subprocess.CalledProcessError without stderr."""

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            stderr=None,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    exit_code = run_check()
    assert exit_code == 1

    captured = capsys.readouterr()
    assert (
        "Command '['git', 'diff', '--cached', '--name-only', '--diff-filter=AM']' returned non-zero exit status 1."
        in captured.err
    )
