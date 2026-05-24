"""Pre-commit check enforcing max lines on newly added staged Python files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def list_added_staged_python_files(repo_root: Path | None = None) -> list[Path]:
    """Return newly added staged .py files from git index."""
    completed = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    paths = [Path(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
    return [path for path in paths if path.suffix == ".py"]


def count_lines(file_path: Path, repo_root: Path | None = None) -> int:
    """Return total line count for a text file."""
    resolved = (repo_root / file_path) if repo_root is not None else file_path
    content = resolved.read_text(encoding="utf-8", errors="replace")
    return len(content.splitlines())


def find_line_limit_violations(
    files: list[Path], max_lines: int, repo_root: Path | None = None
) -> list[tuple[Path, int]]:
    """Return files exceeding the configured max line count."""
    violations: list[tuple[Path, int]] = []
    for file_path in files:
        line_count = count_lines(file_path, repo_root=repo_root)
        if line_count > max_lines:
            violations.append((file_path, line_count))
    return violations


def run_check(max_lines: int, repo_root: Path | None = None) -> int:
    """Validate newly added staged Python files against max line threshold."""
    try:
        new_python_files = list_added_staged_python_files(repo_root=repo_root)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        print(f"max-lines-new-py: failed to inspect staged files: {stderr}", file=sys.stderr)
        return 1

    violations = find_line_limit_violations(
        new_python_files, max_lines=max_lines, repo_root=repo_root
    )
    if not violations:
        return 0

    print(f"max-lines-new-py: line limit is {max_lines}.")
    for file_path, line_count in violations:
        print(f"  {file_path.as_posix()}: {line_count} lines")
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the line-limit checker."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-lines", type=int, default=200, help="Maximum allowed file lines.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the checker CLI and return process exit code."""
    args = parse_args(argv)
    return run_check(max_lines=args.max_lines, repo_root=Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
