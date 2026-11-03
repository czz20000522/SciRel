"""Claude PreToolUse hook for file-tool-only workers in one private lane.

This is a file-tool guard, not an OS sandbox or an output-blind read boundary.
Do not give these workers Bash, NotebookEdit, MCP mutation tools or recursive Agent.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


def allowed(lane: Path, tool: str, parameters: dict, cwd: Path) -> bool:
    if tool not in {"Write", "Edit"}:
        return False
    if not isinstance(parameters, dict):
        return False
    target = parameters.get("file_path")
    if not isinstance(target, str) or not target:
        return False
    path = Path(target)
    if not path.is_absolute():
        path = cwd / path
    try:
        root = lane.resolve(strict=True)
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or resolved == root:
            return False
        # Existing symlinks are disallowed, even when they currently point into the lane.
        for parent in [path, *path.parents]:
            if parent.is_symlink():
                return False
        return root.is_dir()
    except (OSError, RuntimeError):
        return False


def main() -> int:
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one private lane argument")
        event = json.load(sys.stdin)
        if allowed(Path(sys.argv[1]), event.get("tool_name", ""),
                   event.get("tool_input", {}), Path(event.get("cwd", "."))):
            return 0
    except (ValueError, TypeError, OSError):
        pass
    print("Worker file write denied: use only the assigned private lane.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
