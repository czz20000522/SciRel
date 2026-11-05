"""Static inventory of the declared public surface in ``src/scirel``.

The installed-wheel validator discovers the public surface by importing the
package. Tests that pin that discovery need an independent expectation, so this
module reads the *source tree* with :mod:`ast` and never imports SciRel or its
scientific dependencies. A source/runtime mismatch is then a real failure
instead of a tautology, and the inventory follows the tree when exports are
added or removed.

Only literal ``__all__`` declarations are accepted. A computed or malformed
``__all__`` raises :class:`SurfaceInventoryError`, so the tests fail closed
instead of silently under-counting the public surface.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "src" / "scirel"


class SurfaceInventoryError(RuntimeError):
    """Raised when the source tree does not declare a resolvable surface."""


def _declared_names(initializer: Path) -> tuple[str, ...]:
    """Return the literal ``__all__`` names declared by one initializer."""
    try:
        module = ast.parse(initializer.read_text(encoding="utf-8"), filename=str(initializer))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise SurfaceInventoryError(f"cannot parse {initializer}: {exc}") from exc

    for node in module.body:
        value: Any = None
        targets: tuple[ast.expr, ...] = ()
        if isinstance(node, ast.Assign):
            targets, value = tuple(node.targets), node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = (node.target,), node.value
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        try:
            names = ast.literal_eval(value)
        except (ValueError, TypeError, SyntaxError) as exc:
            raise SurfaceInventoryError(f"{initializer} declares a non-literal __all__") from exc
        if not isinstance(names, (list, tuple)) or not all(
            isinstance(name, str) and name for name in names
        ):
            raise SurfaceInventoryError(f"{initializer} declares an invalid __all__")
        if len(set(names)) != len(names):
            raise SurfaceInventoryError(f"{initializer} declares duplicate __all__ names")
        return tuple(names)

    raise SurfaceInventoryError(f"{initializer} does not declare __all__")


def _package_directories(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.iterdir()
            if path.is_dir() and not path.name.startswith("_") and (path / "__init__.py").is_file()
        )
    )


def public_domains(root: Path = SOURCE_ROOT) -> tuple[str, ...]:
    """Public top-level domain packages, in source-tree order."""
    return tuple(path.name for path in _package_directories(root))


def domain_exports(domain: str, root: Path = SOURCE_ROOT) -> tuple[str, ...]:
    """The declared ``__all__`` of one top-level public domain."""
    initializer = root / domain / "__init__.py"
    if not initializer.is_file():
        raise SurfaceInventoryError(f"public domain {domain!r} has no initializer")
    return _declared_names(initializer)


def _nested_module_initializer(package_dir: Path, name: str) -> Path:
    direct = package_dir / f"{name}.py"
    if direct.is_file():
        return direct
    initializer = package_dir / name / "__init__.py"
    if initializer.is_file():
        return initializer
    raise SurfaceInventoryError(
        f"nested package {package_dir.name!r} exports {name!r} without a module"
    )


def nested_packages(root: Path = SOURCE_ROOT) -> dict[str, tuple[str, ...]]:
    """Public packages nested below a domain and the modules each declares.

    Keys are dotted package names relative to ``scirel`` (for example
    ``kinetic.dispersion``); values are that package's ``__all__``.
    """
    nested: dict[str, tuple[str, ...]] = {}
    for directory in _package_directories(root):
        for child in sorted(directory.iterdir()):
            if (
                not child.is_dir()
                or child.name.startswith(("_", "."))
                or not (child / "__init__.py").is_file()
            ):
                continue
            names = _declared_names(child / "__init__.py")
            package_name = f"{directory.name}.{child.name}"
            for name in names:
                _nested_module_initializer(child, name)
            nested[package_name] = names
    return nested


def surface_counts(root: Path = SOURCE_ROOT) -> dict[str, int]:
    """Deterministic counts the installed-wheel surface check must reproduce."""
    counts = {
        "domain_count": 0,
        "export_count": 0,
        "nested_package_count": 0,
        "nested_module_count": 0,
        "nested_export_count": 0,
    }
    for domain in public_domains(root):
        counts["domain_count"] += 1
        counts["export_count"] += len(domain_exports(domain, root))
    for package_name, modules in nested_packages(root).items():
        counts["nested_package_count"] += 1
        package_dir = root.joinpath(*package_name.split("."))
        for name in modules:
            counts["nested_module_count"] += 1
            counts["nested_export_count"] += len(
                _declared_names(_nested_module_initializer(package_dir, name))
            )
    return counts
