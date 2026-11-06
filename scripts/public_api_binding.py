"""Shared public/implementation binding helpers for release tooling.

Asset documents historically stored the implementation module and symbol in
``public_api.python``.  Newer documents may additionally declare a stable
package-level import with ``canonical_module`` and ``canonical_symbol``.  The
implementation binding remains the source and wheel closure authority; the
canonical binding is a discoverable compatibility alias.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import inspect
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _SignatureReference:
    """Render a callable default by its stable import reference."""

    reference: str

    def __repr__(self) -> str:
        return self.reference


def contract_default(value: Any) -> Any:
    """Return a deterministic, JSON-compatible value for a signature default."""

    if callable(value):
        module = getattr(value, "__module__", None)
        qualname = getattr(value, "__qualname__", None)
        if module and qualname:
            return f"{module}.{qualname}"
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError):
        return value


def format_signature(signature: inspect.Signature) -> str:
    """Format a signature with stable references for callable defaults."""

    parameters = []
    for parameter in signature.parameters.values():
        if parameter.default is not inspect.Parameter.empty and callable(parameter.default):
            reference = contract_default(parameter.default)
            if isinstance(reference, str):
                parameter = parameter.replace(default=_SignatureReference(reference))
        parameters.append(parameter)
    return str(signature.replace(parameters=parameters))


def _module_path(source_root: Path, module: str) -> tuple[Path, Path]:
    """Return the direct-module and package-initializer candidates."""

    relative = Path("src", *module.split("."))
    return relative.with_suffix(".py"), relative / "__init__.py"


def source_module_path(source_root: Path, module: str) -> Path:
    """Resolve a SciRel module to its source file, including package roots."""

    direct, package = _module_path(source_root, module)
    if (source_root / direct).is_file():
        return direct
    if (source_root / package).is_file():
        return package
    raise ValueError(f"source module is absent from checkout: {module}")


def _initializer_export_target(initializer: Path, symbol: str) -> str | None:
    """Find a lazy/eager initializer's child module for one exported symbol."""

    try:
        tree = ast.parse(initializer.read_text(encoding="utf-8"), filename=str(initializer))
    except (OSError, UnicodeError, SyntaxError):
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            if not any(
                isinstance(target, ast.Name) and target.id == "_LAZY_EXPORTS" for target in targets
            ):
                continue
            if isinstance(node.value, ast.Dict):
                entries = zip(node.value.keys, node.value.values)
                for key, value in entries:
                    if not isinstance(key, ast.Constant) or key.value != symbol:
                        continue
                    if not isinstance(value, ast.Tuple) or not value.elts:
                        continue
                    module = value.elts[0]
                    if isinstance(module, ast.Constant) and isinstance(module.value, str):
                        return module.value
            elif isinstance(node.value, ast.DictComp):
                # A compact package facade may map every name in ``__all__``
                # to the same child module, e.g. ``{name: ("eqdsk", name)
                # for name in __all__}``.
                key = node.value.key
                value = node.value.value
                if (
                    isinstance(key, ast.Name)
                    and isinstance(value, ast.Tuple)
                    and len(value.elts) >= 2
                    and isinstance(value.elts[0], ast.Constant)
                    and isinstance(value.elts[0].value, str)
                    and isinstance(value.elts[1], ast.Name)
                    and value.elts[1].id == key.id
                    and any(
                        isinstance(generator.target, ast.Name) and generator.target.id == key.id
                        for generator in node.value.generators
                    )
                ):
                    return value.elts[0].value
        elif isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            if any(alias.name == symbol or alias.asname == symbol for alias in node.names):
                return node.module
    return None


def implementation_module(source_root: Path, module: str, symbol: str) -> str:
    """Resolve a package-root legacy binding to its child implementation.

    A package-root document is retained for compatibility.  When its
    initializer explicitly maps the symbol to a child module, staging and
    release tooling bind that child module as the implementation file while
    leaving the package root as the public import path.
    """

    direct, package = _module_path(source_root, module)
    if (source_root / direct).is_file():
        return module
    initializer = source_root / package
    if not initializer.is_file():
        raise ValueError(f"source module is absent from checkout: {module}")
    child = _initializer_export_target(initializer, symbol)
    if child:
        return f"{module}.{child.lstrip('.')}"
    raise ValueError(
        f"package-root public API has no child implementation mapping: {module}.{symbol}"
    )


def canonical_binding(python_api: dict[str, Any]) -> tuple[str, str]:
    """Return the explicit canonical package binding or legacy fallback."""

    return (
        python_api.get("canonical_module", python_api["module"]),
        python_api.get("canonical_symbol", python_api["symbol"]),
    )


def has_explicit_canonical_binding(python_api: dict[str, Any]) -> bool:
    return "canonical_module" in python_api or "canonical_symbol" in python_api


def qualified_name(module: str, symbol: str) -> str:
    return f"{module}.{symbol}"
