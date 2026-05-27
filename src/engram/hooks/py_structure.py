"""Pre-commit hook enforcing Python file structure rules."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_LINES_TOPLEVEL = 150  # src/<pkg>/file.py (depth-3 paths)
MAX_LINES_SUBPACKAGE = 250  # src/<pkg>/<sub>/file.py (depth-4+ paths)
MAX_PUBLIC_SYMBOLS = 8


def get_staged_python_files(repo_root: Path | None = None) -> list[Path]:
    """Return added/modified staged .py files from git index."""
    completed = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    paths = [Path(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
    return [path for path in paths if path.suffix == ".py"]


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
                    f"  → Split into a subpackage or extract helpers to a sibling module."
                )

        # Check symbol count (skip test files)
        if not is_test_file(file_path):
            n_symbols = count_public_symbols(file_path, repo_root=repo_root)
            if n_symbols > MAX_PUBLIC_SYMBOLS:
                violations.append(
                    f"  {posix_path}: {n_symbols} public symbols (limit: {MAX_PUBLIC_SYMBOLS})\n"
                    f"  → Extract related functions/classes into a sibling module."
                )

    return violations


def run_check(repo_root: Path | None = None) -> int:
    """Run structure check and return exit code (0=pass, 1=fail)."""
    try:
        files = get_staged_python_files(repo_root=repo_root)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        print(f"py-structure: failed to inspect staged files: {stderr}", file=sys.stderr)  # noqa: T201
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
    return run_check(repo_root=Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
