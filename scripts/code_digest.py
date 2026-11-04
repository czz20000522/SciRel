"""Digests of what affects behaviour, for correctness evidence.

Evidence that a function works should go stale when its behaviour can change, and not when
someone edits a docstring, a comment or the layout. So a Python file is digested through its
syntax tree with docstrings removed, and a contract through the fields that define the call.
Other files, such as data, are digested by their bytes.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

CONTRACT_BEHAVIOUR_FIELDS = ("public_api", "inputs", "outputs", "example")
_DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _canonical(node):
    """Serialize a syntax tree without positions, stable across Python versions.

    Empty optional fields are dropped, so a field added by a newer Python does not change
    the digest of code that does not use it.
    """
    if isinstance(node, ast.AST):
        body = getattr(node, "body", None)
        fields = {}
        for name, value in ast.iter_fields(node):
            if (
                name == "body"
                and isinstance(node, _DOCUMENTED)
                and body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                value = body[1:]
            value = _canonical(value)
            if value not in (None, []):
                fields[name] = value
        return [type(node).__name__, fields]
    if isinstance(node, list):
        return [_canonical(item) for item in node]
    if isinstance(node, (str, int, float, bool)) or node is None:
        return node
    return repr(node)  # bytes, complex and Ellipsis constants


def source_digest(path: str | Path) -> str:
    """Digest a file for correctness evidence: behaviour for Python, bytes for anything else."""
    path = Path(path)
    data = path.read_bytes()
    if path.suffix != ".py":
        return hashlib.sha256(data).hexdigest()
    tree = _canonical(ast.parse(data))
    return hashlib.sha256(json.dumps(tree, sort_keys=True).encode("utf-8")).hexdigest()


def contract_digest(path: str | Path) -> str:
    """Digest the part of a contract that says how to call the function and what it returns."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    selected = {name: document.get(name) for name in CONTRACT_BEHAVIOUR_FIELDS}
    return hashlib.sha256(json.dumps(selected, sort_keys=True).encode("utf-8")).hexdigest()
