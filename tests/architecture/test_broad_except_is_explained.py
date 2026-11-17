"""A broad `except Exception` in `src/` must explain why a narrower type cannot work.

The code-style rule says a broad catch needs a comment, and that it must not turn a
programming error into a physics status. The second half is a judgement call; the
first half is mechanical, so this test enforces it and nothing more:

* every broad handler (`except Exception`, `except BaseException`, bare `except:`) in
  `src/scirel/**` carries a comment on the same line or the line above;
* prose elsewhere is unaffected.

**What it does not catch**: whether the comment is true, or whether the handler
reclassifies a bug as a status. Those need review; the test only stops the silent
broad catch from spreading without a stated reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "scirel"


def broad_handlers(path: Path) -> list[ast.ExceptHandler]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            found.append(node)
            continue
        names = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
        for item in names:
            if isinstance(item, ast.Name) and item.id in {"Exception", "BaseException"}:
                found.append(node)
                break
    return found


def is_broad(handler: ast.ExceptHandler) -> bool:
    return True


def has_explanation(lines: list[str], handler: ast.ExceptHandler) -> bool:
    """A comment on the handler line, the first non-blank line above, or the handler body head.

    Accepting a comment as the first line of the body matters because that is where
    Python convention puts it: the reason belongs to the block it justifies, not to
    the statement above it.
    """
    index = handler.lineno - 1
    if "#" in lines[index]:
        return True
    probe = index - 1
    while probe >= 0 and not lines[probe].strip():
        probe -= 1
    if probe >= 0 and lines[probe].lstrip().startswith("#"):
        return True
    body = index + 1
    while body < len(lines) and not lines[body].strip():
        body += 1
    return body < len(lines) and lines[body].lstrip().startswith("#")


def offenders(root: Path) -> list[str]:
    hits = []
    for path in sorted(root.glob("**/*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for handler in broad_handlers(path):
            if not has_explanation(lines, handler):
                hits.append(f"{path.relative_to(root.parents[1]).as_posix()}:{handler.lineno}")
    return hits


def test_every_broad_handler_in_src_explains_itself():
    assert offenders(SOURCE) == [], (
        "broad except without a stated reason (code-style: 'A broad `except Exception` "
        "needs a comment explaining why a narrower type cannot work'):\n  "
        + "\n  ".join(offenders(SOURCE))
    )


def test_the_guard_would_catch_an_unexplained_handler(tmp_path: Path):
    source = tmp_path / "src" / "scirel"
    source.mkdir(parents=True)
    (source / "bad.py").write_text(
        "def f():\n    try:\n        return 1\n    except Exception:\n        return 2\n",
        encoding="utf-8",
    )
    assert offenders(source) == ["src/scirel/bad.py:4"]


def test_a_comment_above_or_on_the_line_is_accepted(tmp_path: Path):
    source = tmp_path / "src" / "scirel"
    source.mkdir(parents=True)
    (source / "ok.py").write_text(
        "def f():\n"
        "    try:\n"
        "        return 1\n"
        "    # restore then re-raise; nothing is swallowed\n"
        "    except Exception:\n"
        "        return 2\n"
        "\n"
        "def g():\n"
        "    try:\n"
        "        return 1\n"
        "    except Exception:  # documented on the line itself\n"
        "        return 2\n",
        encoding="utf-8",
    )
    assert offenders(source) == []
