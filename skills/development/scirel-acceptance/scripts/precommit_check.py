#!/usr/bin/env python3
"""Fast checks on staged files. The complete check is check_all.py in this directory."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt", ".rst", ".sh"}
FORBIDDEN = {
    "private path": re.compile(r"/Users/[a-z]|/home/[a-z]+/|[A-Z]:[/\\]software|/srv/scirel"),
    "secret": re.compile(
        r"ghp_[A-Za-z0-9]{20}|github_pat_|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE"
    ),
}
# These files define or test the patterns above.
EXEMPT = {
    "skills/development/scirel-acceptance/scripts/precommit_check.py",
    "tests/architecture/test_repository_skeleton.py",
    "tests/tooling/test_precommit_check.py",
}


def staged() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [name for name in out.split("\0") if name]


def scan(names: list[str], read=None) -> list[str]:
    def read_staged(name):
        return subprocess.run(
            ["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=True
        ).stdout

    read = read or read_staged
    errors = []
    for name in names:
        if Path(name).suffix not in TEXT_SUFFIXES or name in EXEMPT:
            continue
        text = read(name).decode("utf-8", errors="replace")
        for label, pattern in FORBIDDEN.items():
            if match := pattern.search(text):
                errors.append(f"{name}: {label}: {match.group(0)}")
    return errors


def lint(names: list[str]) -> list[str]:
    targets = [
        name for name in names if name.endswith(".py") and name.startswith(("src/", "tests/"))
    ]
    if not targets:
        return []
    ruff = [sys.executable, "-m", "ruff"]
    errors = []
    for command in (
        [*ruff, "check", "--quiet", *targets],
        [*ruff, "format", "--check", "--quiet", *targets],
    ):
        done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if done.returncode:
            errors.append((done.stdout + done.stderr).strip() or f"failed: {' '.join(command)}")
    return errors


def main() -> int:
    names = staged()
    errors = scan(names) + lint(names)
    for error in errors:
        print("ERROR:", error)
    if errors:
        print("Fix these, stage again and commit. See the scirel-acceptance skill.")
        return 1
    print(f"pre-commit: PASS ({len(names)} staged files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
