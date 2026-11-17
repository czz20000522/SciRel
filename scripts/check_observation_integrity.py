"""Check that failed observations carry their reason, instead of discarding it.

Why this exists
---------------
A check that cannot distinguish "it failed" from "it did not run" is worse than no
check: it does not fail, it hands the reader a gap to fill with a guess. In this
repository the most expensive instance was a test that failed six times in the release
stage and passed alone. The failure surfaced as a bare

    CalledProcessError: Command '[...]' returned non-zero exit status 128

because the helper ran ``subprocess.run(..., check=True, capture_output=True)`` and
threw stderr away. Two "fixes" were shipped on guesses (a timeout, then the lock)
before the actual reason appeared: a local ``git clone`` had failed to copy an object
file. Carrying stderr into the raised error turned six runs of guessing into one run
of reading.

The rule this enforces is narrow on purpose: a ``subprocess.run`` that both captures
output and raises on failure must have its failure handled where ``stderr`` is
available, normally by catching ``subprocess.CalledProcessError`` and including
``.stderr`` in the replacement error. Deliberate exceptions are allowed but must say
why on the line above, so a reader sees the decision rather than the absence of one.

This is one check for one class. `docs/maintainer/observation-integrity.md` records the
class and the other instances it covers.

Exit codes are the three states: 0 = no new silent site, 1 = a new silent site, 2 = nothing
was observed because the given root has none of ``scripts/``, ``tests/`` or ``src/``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", "node_modules", "build", "dist"}
SCAN_DIRS = ("scripts", "tests", "src")

# A call may opt out explicitly. The marker must appear in the three-source-line window
# above the call, together with a reason: a bare marker with no words is the same
# "nobody looked" that this check exists to prevent.
MARKER = "observation-integrity: no-stderr-on-purpose"


def _mentions_stderr(node: ast.AST) -> bool:
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute) and inner.attr == "stderr":
            return True
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
            # ``"... stderr ..."`` inside a message counts: the reason survives in text.
            if "stderr" in inner.value:  # pragma: no cover
                return True
    return False


def _handler_covers(handlers: list[ast.ExceptHandler]) -> bool:
    """True when some handler both catches the failure and keeps its stderr."""
    for handler in handlers:
        caught = handler.type
        names = []
        if isinstance(caught, ast.Tuple):
            names = [n for n in caught.elts]
        elif caught is not None:
            names = [caught]
        mentions_called_process = any(
            (isinstance(n, ast.Attribute) and n.attr == "CalledProcessError")
            or (isinstance(n, ast.Name) and n.id == "CalledProcessError")
            for n in names
        )
        if not mentions_called_process:
            # A bare `except Exception` also covers it, but only counts when the body
            # actually keeps stderr; otherwise it is the same silent loss.
            if not mentions_called_process and not _mentions_stderr(handler):
                continue
        if _mentions_stderr(handler):
            return True
    return False


def _is_silent_run(node: ast.Call) -> bool:
    if not (isinstance(node.func, ast.Attribute) and node.func.attr == "run"):
        return False
    keywords = {kw.arg for kw in node.keywords}
    if "capture_output" not in keywords or "check" not in keywords:
        return False
    check = next(kw.value for kw in node.keywords if kw.arg == "check")
    capture = next(kw.value for kw in node.keywords if kw.arg == "capture_output")
    return (
        isinstance(check, ast.Constant)
        and check.value is True
        and isinstance(capture, ast.Constant)
        and capture.value is True
    )


def _has_marker(lines: list[str], lineno: int) -> bool:
    window = lines[max(0, lineno - 4) : lineno]
    for line in window:
        if MARKER in line:
            # require some prose after the marker
            tail = line.split(MARKER, 1)[1].strip(" :#-")
            if len(tail) >= 12:
                return True
    return False


def scan_text(path: str, text: str) -> list[dict]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines()
    problems: list[dict] = []

    def walk(node: ast.AST, enclosing_handlers: list[ast.ExceptHandler]) -> None:
        if isinstance(node, ast.Try):
            covered = enclosing_handlers + (
                list(node.handlers) if _handler_covers(list(node.handlers)) else []
            )
            for child in node.body:
                walk(child, covered)
            for handler in node.handlers:
                for child in handler.body:
                    walk(child, enclosing_handlers)
            for child in node.orelse + node.finalbody:
                walk(child, enclosing_handlers)
            return
        if (
            isinstance(node, ast.Call)
            and _is_silent_run(node)
            and not enclosing_handlers
            and not _has_marker(lines, node.lineno)
        ):
            problems.append(
                {
                    "path": path,
                    "line": node.lineno,
                    "message": (
                        "subprocess.run(check=True, capture_output=True) without a handler that "
                        "keeps stderr; a failure here reports a bare exit status"
                    ),
                }
            )
        for child in ast.iter_child_nodes(node):
            walk(child, enclosing_handlers)

    walk(tree, [])
    return problems


def scan_tree(root: Path) -> list[dict]:
    problems: list[dict] = []
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if SKIP_DIRS & set(path.parts):
                continue
            problems.extend(
                scan_text(str(path.relative_to(root)), path.read_text(encoding="utf-8"))
            )
    return problems


def load_baseline(root: Path) -> dict[str, int]:
    """Read the ratchet. Missing file means nothing is tolerated."""
    path = root / "tools" / "docs" / "observation-baseline.json"
    if not path.is_file():
        return {}
    import json

    document = json.loads(path.read_text(encoding="utf-8"))
    return {entry["path"]: int(entry["count"]) for entry in document.get("entries", [])}


def apply_baseline(problems: list[dict], baseline: dict[str, int]) -> tuple[list[dict], list[dict]]:
    """Split problems into (blocking, tolerated-because-already-recorded)."""
    seen: dict[str, int] = {}
    blocking, tolerated = [], []
    for problem in problems:
        path = problem["path"]
        seen[path] = seen.get(path, 0) + 1
        if seen[path] > baseline.get(path, 0):
            blocking.append(problem)
        else:
            tolerated.append(problem)
    return blocking, tolerated


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    # "Nothing to scan" is not "nothing found". Scanning an empty tree would print the same
    # success line as a clean run, so it gets its own exit code instead of an empty pass.
    if not root.is_dir():
        print(f"observation integrity: {root} is not a directory; nothing was observed")
        return 2
    if not any((root / name).is_dir() for name in SCAN_DIRS):
        print(
            f"observation integrity: {root} has none of {', '.join(SCAN_DIRS)}; nothing was observed"
        )
        return 2
    problems = scan_tree(root)
    blocking, tolerated = apply_baseline(problems, load_baseline(root))
    if not blocking:
        print(
            "observation integrity: no new silent failure; "
            f"{len(tolerated)} recorded site(s) still on the ratchet"
        )
        return 0
    for problem in blocking:
        print(f"{problem['path']}:{problem['line']}: {problem['message']}")
    print(f"observation integrity: {len(blocking)} new problem(s); the ratchet only shrinks")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
