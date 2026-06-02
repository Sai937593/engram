"""Pre-commit hook enforcing Python file structure rules."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MAX_LINES_TOPLEVEL = 150  # src/<pkg>/file.py (depth-3 paths)
MAX_LINES_SUBPACKAGE = 200  # src/<pkg>/<sub>/file.py (depth-4+ paths)
MAX_PUBLIC_SYMBOLS = 8
L1_GUARDRAIL_RULES: tuple[tuple[str, str], ...] = (
    (
        "Python file size limits",
        "Keep non-test Python files within py-structure limits: "
        f"<= {MAX_LINES_TOPLEVEL} lines for top-level src files and "
        f"<= {MAX_LINES_SUBPACKAGE} lines for subpackage files.",
    ),
    (
        "Python public symbol limit",
        "Keep non-test Python files within the py-structure public symbol limit: "
        f"<= {MAX_PUBLIC_SYMBOLS} top-level def/class symbols per file.",
    ),
)


def _collect_git_paths(args: list[str], repo_root: Path | None = None) -> list[Path]:
    completed = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    return [Path(line.strip()) for line in completed.stdout.splitlines() if line.strip()]


def _filter_python_files(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.suffix == ".py"]


def get_staged_python_files(repo_root: Path | None = None) -> list[Path]:
    """Return added/modified staged .py files from git index."""
    return _filter_python_files(
        _collect_git_paths(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"], repo_root=repo_root
        )
    )


def get_changed_python_files(repo_root: Path | None = None) -> list[Path]:
    """Return staged, unstaged modified, and untracked .py files."""
    seen: dict[Path, None] = {}
    for args in (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        ["git", "diff", "--name-only", "--diff-filter=M"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        for path in _filter_python_files(_collect_git_paths(args, repo_root=repo_root)):
            seen.setdefault(path, None)
    return list(seen.keys())


def is_test_file(path: Path) -> bool:
    """Return True if path is inside a tests/ directory."""
    return "tests" in path.parts


def get_line_limit(path: Path) -> int | None:
    """Return line limit for file, or None if file is exempt (test files)."""
    if is_test_file(path):
        return None
    if path.parts and path.parts[0] == "src":
        if len(path.parts) == 3:
            return MAX_LINES_TOPLEVEL
        if len(path.parts) >= 4:
            return MAX_LINES_SUBPACKAGE
    return MAX_LINES_SUBPACKAGE  # safe default for any other .py


def count_lines(path: Path, repo_root: Path | None = None) -> int:
    """Return total line count for a file."""
    resolved = (repo_root / path) if repo_root is not None else path
    content = resolved.read_text(encoding="utf-8", errors="replace")
    return len(content.splitlines())


def count_public_symbols(path: Path, repo_root: Path | None = None) -> int:
    """Count top-level def/class statements (column 0) in a file."""
    resolved = (repo_root / path) if repo_root is not None else path
    content = resolved.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"^(def |class )\w", re.MULTILINE)
    return len(pattern.findall(content))


def check_files(files: list[Path], repo_root: Path | None = None) -> list[str]:
    """Return a list of human-readable violation messages."""
    violations: list[str] = []
    for file_path in files:
        resolved = (repo_root / file_path) if repo_root is not None else file_path
        if not resolved.exists():
            continue

        posix_path = file_path.as_posix()

        # Check line limit
        limit = get_line_limit(file_path)
        if limit is not None:
            n_lines = count_lines(file_path, repo_root=repo_root)
            if n_lines > limit:
                tier = "top-level" if limit == MAX_LINES_TOPLEVEL else "subpackage"
                violations.append(
                    f"  {posix_path}: {n_lines} lines (limit: {limit} for {tier} files)\n"
                    f"  \u2192 Split into a subpackage or extract helpers to a sibling module."
                )

        # Check symbol count (skip test files)
        if not is_test_file(file_path):
            n_symbols = count_public_symbols(file_path, repo_root=repo_root)
            if n_symbols > MAX_PUBLIC_SYMBOLS:
                violations.append(
                    f"  {posix_path}: {n_symbols} public symbols (limit: {MAX_PUBLIC_SYMBOLS})\n"
                    f"  \u2192 Extract related functions/classes into a sibling module."
                )

    return violations


def run_check(repo_root: Path | None = None, changed: bool = False) -> int:
    """Run structure check and return exit code (0=pass, 1=fail)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    inspection_label = "changed files" if changed else "staged files"
    try:
        files = (
            get_changed_python_files(repo_root=repo_root)
            if changed
            else get_staged_python_files(repo_root=repo_root)
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        sys.stderr.write(f"py-structure: failed to inspect {inspection_label}: {stderr}\n")
        return 1

    violations = check_files(files, repo_root=repo_root)
    if not violations:
        return 0

    print("py-structure violations found:")  # noqa: T201
    for violation in violations:
        print(violation)  # noqa: T201
    return 1


def main() -> int:
    """Entry point for pre-commit hook."""
    parser = argparse.ArgumentParser(description="Run the py_structure hook.")
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Check staged, unstaged modified, and untracked Python files.",
    )
    args = parser.parse_args()
    return run_check(repo_root=Path.cwd(), changed=bool(args.changed))


if __name__ == "__main__":
    raise SystemExit(main())
